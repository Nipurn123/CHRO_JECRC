class CustomAgent:
    async def click_element(self, selector):
        # Remove highlighting options
        await self.page.click(selector, 
            force=True,  # Skip hover highlighting
            no_wait_after=True,  # Don't wait for animations
            timeout=5000
        )
    
    async def type_text(self, selector, text):
        # Remove highlighting for input fields
        await self.page.fill(selector, text,
            force=True,
            no_wait_after=True
        )# -*- coding: utf-8 -*-
# @Time    : 2025/1/2
# @Author  : nipurnagarwal
# @ProjectName: browser-use-100XPrompt
# @FileName: custom_agent.py

import json
import logging
import pdb
import traceback
from typing import Optional, Type, Any, Dict, List, Union
from PIL import Image, ImageDraw, ImageFont
import os
import base64
import io
import asyncio
import random
import time

from browser_use.agent.prompts import SystemPrompt
from browser_use.agent.service import Agent
from browser_use.agent.views import (
    ActionResult,
    AgentHistoryList,
    AgentOutput,
)
from browser_use.browser.browser import Browser
from browser_use.browser.context import BrowserContext
from browser_use.controller.service import Controller
from browser_use.telemetry.views import (
    AgentEndTelemetryEvent,
    AgentRunTelemetryEvent,
    AgentStepErrorTelemetryEvent,
)
from browser_use.utils import time_execution_async
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    BaseMessage,
)

from .custom_massage_manager import CustomMassageManager
from .custom_views import CustomAgentOutput, CustomAgentStepInfo
from .file_system_agent import FileSystemAgent
from ..exceptions import PromptException, InvalidOpenAIResponseFormat, TaskNotFound, UnexpectedTaskStatus, DisabledFeature
logger = logging.getLogger(__name__)

# Make sure EnhancedCustomAgent is properly defined and exported
__all__ = ['CustomAgent', 'EnhancedCustomAgent']


class CustomAgent(Agent):
    def __init__(
            self,
            task: str,
            llm: BaseChatModel,
            add_infos: str = "",
            browser: Browser | None = None,
            browser_context: BrowserContext | None = None,
            controller: Controller = Controller(),
            use_vision: bool = True,
            save_conversation_path: Optional[str] = None,
            max_failures: int = 5,
            retry_delay: int = 10,
            system_prompt_class: Type[SystemPrompt] = SystemPrompt,
            max_input_tokens: int = 128000,
            validate_output: bool = False,
            include_attributes: list[str] = [
                "title",
                "type",
                "name",
                "role",
                "tabindex",
                "aria-label",
                "placeholder",
                "value",
                "alt",
                "aria-expanded",
            ],
            max_error_length: int = 400,
            max_actions_per_step: int = 10,
            tool_call_in_content: bool = True,
            stop_event: Optional[asyncio.Event] = None,
    ):
        super().__init__(
            task=task,
            llm=llm,
            browser=browser,
            browser_context=browser_context,
            controller=controller,
            use_vision=use_vision,
            save_conversation_path=save_conversation_path,
            max_failures=max_failures,
            retry_delay=retry_delay,
            system_prompt_class=system_prompt_class,
            max_input_tokens=max_input_tokens,
            validate_output=validate_output,
            include_attributes=include_attributes,
            max_error_length=max_error_length,
            max_actions_per_step=max_actions_per_step,
            tool_call_in_content=tool_call_in_content,
        )
        self.add_infos = add_infos
        self.message_manager = CustomMassageManager(
            llm=self.llm,
            task=self.task,
            action_descriptions=self.controller.registry.get_prompt_description(),
            system_prompt_class=self.system_prompt_class,
            max_input_tokens=self.max_input_tokens,
            include_attributes=self.include_attributes,
            max_error_length=self.max_error_length,
            max_actions_per_step=self.max_actions_per_step,
            tool_call_in_content=tool_call_in_content,
        )
        self.stop_event = stop_event
        self.step_info = None

    def _setup_action_models(self) -> None:
        """Setup dynamic action models from controller's registry"""
        # Get the dynamic action model from controller's registry
        self.ActionModel = self.controller.registry.create_action_model()
        # Create output model with the dynamic actions
        self.AgentOutput = CustomAgentOutput.type_with_custom_actions(self.ActionModel)

    def _log_response(self, response: CustomAgentOutput) -> None:
        """Log the model's response"""
        if "Success" in response.current_state.prev_action_evaluation:
            emoji = "✅"
        elif "Failed" in response.current_state.prev_action_evaluation:
            emoji = "❌"
        else:
            emoji = "🤷"

        logger.info(f"{emoji} Eval: {response.current_state.prev_action_evaluation}")
        logger.info(f"🧠 New Memory: {response.current_state.important_contents}")
        logger.info(f"⏳ Task Progress: {response.current_state.completed_contents}")
        logger.info(f"🤔 Thought: {response.current_state.thought}")
        logger.info(f"🎯 Summary: {response.current_state.summary}")
        for i, action in enumerate(response.action):
            logger.info(
                f"🛠️  Action {i + 1}/{len(response.action)}: {action.model_dump_json(exclude_unset=True)}"
            )

    def update_step_info(
            self, model_output: CustomAgentOutput, step_info: CustomAgentStepInfo = None
    ):
        """
        update step info
        """
        if step_info is None:
            return

        step_info.step_number += 1
        important_contents = model_output.current_state.important_contents
        if (
                important_contents
                and "None" not in important_contents
                and important_contents not in step_info.memory
        ):
            step_info.memory += important_contents + "\n"

        completed_contents = model_output.current_state.completed_contents
        if completed_contents and "None" not in completed_contents:
            step_info.task_progress = completed_contents

    @time_execution_async("--get_next_action")
    async def get_next_action(self, input_messages: list[BaseMessage]) -> AgentOutput:
        """Get next action from LLM based on current state"""
        try:
            structured_llm = self.llm.with_structured_output(self.AgentOutput, include_raw=True)
            response: dict[str, Any] = await structured_llm.ainvoke(input_messages)  # type: ignore

            parsed: AgentOutput = response['parsed']
            # cut the number of actions to max_actions_per_step
            parsed.action = parsed.action[: self.max_actions_per_step]
            self._log_response(parsed)
            self.n_steps += 1

            return parsed
        except Exception as e:
            # If something goes wrong, try to invoke the LLM again without structured output,
            # and Manually parse the response. Temporarily solution for DeepSeek
            ret = self.llm.invoke(input_messages)
            if isinstance(ret.content, list):
                parsed_json = json.loads(ret.content[0].replace("```json", "").replace("```", ""))
            else:
                parsed_json = json.loads(ret.content.replace("```json", "").replace("```", ""))
            parsed: AgentOutput = self.AgentOutput(**parsed_json)
            if parsed is None:
                raise ValueError(f'Could not parse response.')

            # cut the number of actions to max_actions_per_step
            parsed.action = parsed.action[: self.max_actions_per_step]
            self._log_response(parsed)
            self.n_steps += 1

            return parsed

    @time_execution_async("--step")
    async def step(self, step_info: Optional[CustomAgentStepInfo] = None) -> None:
        """Execute one step of the task"""
        if self.stop_event and self.stop_event.is_set():
            raise asyncio.CancelledError("Agent execution stopped")

        logger.info(f"\n📍 Step {self.n_steps}")
        state = None
        model_output = None
        result: list[ActionResult] = []
        self.step_info = step_info

        try:
            state = await self.browser_context.get_state(use_vision=self.use_vision)
            self.message_manager.add_state_message(state, self._last_result, step_info)
            input_messages = self.message_manager.get_messages()
            model_output = await self.get_next_action(input_messages)
            self.update_step_info(model_output, step_info)
            logger.info(f"🧠 All Memory: {step_info.memory}")
            self._save_conversation(input_messages, model_output)
            self.message_manager._remove_last_state_message()  # we dont want the whole state in the chat history
            self.message_manager.add_model_output(model_output)

            result: list[ActionResult] = await self.controller.multi_act(
                model_output.action, self.browser_context
            )
            self._last_result = result

            if len(result) > 0 and result[-1].is_done:
                logger.info(f"📄 Result: {result[-1].extracted_content}")

            self.consecutive_failures = 0

        except Exception as e:
            result = self._handle_step_error(e)
            self._last_result = result

        finally:
            if not result:
                return
            for r in result:
                if r.error:
                    self.telemetry.capture(
                        AgentStepErrorTelemetryEvent(
                            agent_id=self.agent_id,
                            error=r.error,
                        )
                    )
            if state:
                self._make_history_item(model_output, state, result)

    def create_history_gif(
            self,
            output_path: str = 'agent_history.gif',
            duration: int = 3000,
            show_goals: bool = True,
            show_task: bool = True,
            show_logo: bool = False,
            font_size: int = 40,
            title_font_size: int = 56,
            goal_font_size: int = 44,
            margin: int = 40,
            line_spacing: float = 1.5,
    ) -> None:
        """Create a GIF from the agent's history with overlaid task and goal text."""
        if not self.history.history:
            logger.warning('No history to create GIF from')
            return

        images = []
        # if history is empty or first screenshot is None, we can't create a gif
        if not self.history.history or not self.history.history[0].state.screenshot:
            logger.warning('No history or first screenshot to create GIF from')
            return

        # Try to load nicer fonts
        try:
            # Try different font options in order of preference
            font_options = ['Helvetica', 'Arial', 'DejaVuSans', 'Verdana']
            font_loaded = False

            for font_name in font_options:
                try:
                    import platform
                    if platform.system() == "Windows":
                        # Need to specify the abs font path on Windows
                        font_name = os.path.join(os.getenv("WIN_FONT_DIR", "C:\\Windows\\Fonts"), font_name + ".ttf")
                    regular_font = ImageFont.truetype(font_name, font_size)
                    title_font = ImageFont.truetype(font_name, title_font_size)
                    goal_font = ImageFont.truetype(font_name, goal_font_size)
                    font_loaded = True
                    break
                except OSError:
                    continue

            if not font_loaded:
                raise OSError('No preferred fonts found')

        except OSError:
            regular_font = ImageFont.load_default()
            title_font = ImageFont.load_default()

            goal_font = regular_font

        # Load logo if requested
        logo = None
        if show_logo:
            try:
                logo = Image.open('./static/browser-use.png')
                # Resize logo to be small (e.g., 40px height)
                logo_height = 150
                aspect_ratio = logo.width / logo.height
                logo_width = int(logo_height * aspect_ratio)
                logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
            except Exception as e:
                logger.warning(f'Could not load logo: {e}')

        # Create task frame if requested
        if show_task and self.task:
            task_frame = self._create_task_frame(
                self.task,
                self.history.history[0].state.screenshot,
                title_font,
                regular_font,
                logo,
                line_spacing,
            )
            images.append(task_frame)

        # Process each history item
        for i, item in enumerate(self.history.history, 1):
            if not item.state.screenshot:
                continue

            # Convert base64 screenshot to PIL Image
            img_data = base64.b64decode(item.state.screenshot)
            image = Image.open(io.BytesIO(img_data))

            if show_goals and item.model_output:
                image = self._add_overlay_to_image(
                    image=image,
                    step_number=i,
                    goal_text=item.model_output.current_state.thought,
                    regular_font=regular_font,
                    title_font=title_font,
                    margin=margin,
                    logo=logo,
                )

            images.append(image)

        if images:
            # Save the GIF
            images[0].save(
                output_path,
                save_all=True,
                append_images=images[1:],
                duration=duration,
                loop=0,
                optimize=False,
            )
            logger.info(f'Created GIF at {output_path}')
        else:
            logger.warning('No images found in history to create GIF')

    async def run(self, max_steps: int = 100) -> AgentHistoryList:
        """Execute the task with maximum number of steps"""
        try:
            logger.info(f"🚀 Starting task: {self.task}")

            self.telemetry.capture(
                AgentRunTelemetryEvent(
                    agent_id=self.agent_id,
                    task=self.task,
                )
            )

            step_info = CustomAgentStepInfo(
                task=self.task,
                add_infos=self.add_infos,
                step_number=1,
                max_steps=max_steps,
                memory="",
                task_progress="",
            )

            for step in range(max_steps):
                if self._too_many_failures():
                    break

                try:
                    await self.step(step_info)
                except asyncio.CancelledError:
                    logger.info("Agent execution stopped by user")
                    break

                if self.history.is_done():
                    if (
                            self.validate_output and step < max_steps - 1
                    ):  # if last step, we dont need to validate
                        if not await self._validate_output():
                            continue

                    logger.info("✅ Task completed successfully")
                    break
            else:
                logger.info("❌ Failed to complete task in maximum steps")

            return self.history

        finally:
            self.telemetry.capture(
                AgentEndTelemetryEvent(
                    agent_id=self.agent_id,
                    task=self.task,
                    success=self.history.is_done(),
                    steps=len(self.history.history),
                )
            )
            if not self.injected_browser_context:
                await self.browser_context.close()

            if not self.injected_browser and self.browser:
                await self.browser.close()

            if self.generate_gif:
                self.create_history_gif()


class SemanticAnalyzer:
    """Analyzes semantic content of web pages"""
    
    def __init__(self):
        self.nlp_cache = {}
        
    async def analyze(self, content: str) -> dict:
        """Analyze semantic content of the page"""
        if not content:
            return {}
            
        # Extract key information
        semantic_info = {
            'text_content': content,
            'keywords': self._extract_keywords(content),
            'main_topics': self._identify_topics(content),
            'sentiment': self._analyze_sentiment(content)
        }
        
        return semantic_info
        
    def _extract_keywords(self, text: str) -> list[str]:
        """Extract important keywords from text"""
        # Simple keyword extraction based on frequency
        words = text.lower().split()
        word_freq = {}
        for word in words:
            if len(word) > 3:  # Skip short words
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get top keywords
        keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        return [word for word, _ in keywords]
        
    def _identify_topics(self, text: str) -> list[str]:
        """Identify main topics in the text"""
        # Simple topic identification based on keyword clustering
        keywords = self._extract_keywords(text)
        # Group related keywords
        topics = []
        current_topic = []
        
        for keyword in keywords:
            if not current_topic:
                current_topic.append(keyword)
            elif self._are_related(keyword, current_topic[0]):
                current_topic.append(keyword)
            else:
                topics.append(" ".join(current_topic))
                current_topic = [keyword]
                
        if current_topic:
            topics.append(" ".join(current_topic))
            
        return topics[:3]  # Return top 3 topics
        
    def _analyze_sentiment(self, text: str) -> str:
        """Basic sentiment analysis"""
        positive_words = {'good', 'great', 'excellent', 'amazing', 'wonderful', 'best', 'love'}
        negative_words = {'bad', 'poor', 'terrible', 'worst', 'hate', 'awful', 'horrible'}
        
        words = text.lower().split()
        pos_count = sum(1 for word in words if word in positive_words)
        neg_count = sum(1 for word in words if word in negative_words)
        
        if pos_count > neg_count:
            return 'positive'
        elif neg_count > pos_count:
            return 'negative'
        return 'neutral'
        
    def _are_related(self, word1: str, word2: str) -> bool:
        """Check if two words are semantically related"""
        # Simple check for common prefixes
        return word1[:4] == word2[:4] if len(word1) > 4 and len(word2) > 4 else False


class VisualAnalyzer:
    """Analyzes visual elements and layout of web pages"""
    
    def __init__(self):
        self.cache = {}
        
    async def analyze(self, screenshot) -> dict:
        """Analyze visual elements in the screenshot"""
        if not screenshot:
            return {}
            
        try:
            # Convert base64 screenshot to PIL Image
            img_data = base64.b64decode(screenshot)
            image = Image.open(io.BytesIO(img_data))
            
            # Analyze image
            analysis = {
                'dimensions': image.size,
                'layout_regions': self._detect_regions(image),
                'color_scheme': self._analyze_colors(image),
                'visual_hierarchy': self._analyze_hierarchy(image)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Visual analysis failed: {str(e)}")
            return {}
            
    def _detect_regions(self, image: Image.Image) -> list[dict]:
        """Detect main regions in the image"""
        width, height = image.size
        regions = [
            {'type': 'header', 'bbox': (0, 0, width, height//5)},
            {'type': 'main_content', 'bbox': (0, height//5, width, height*4//5)},
            {'type': 'footer', 'bbox': (0, height*4//5, width, height)}
        ]
        return regions
        
    def _analyze_colors(self, image: Image.Image) -> dict:
        """Analyze color scheme of the page"""
        # Convert image to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
            
        # Get color distribution
        colors = image.getcolors(image.size[0] * image.size[1])
        if not colors:
            return {'dominant_colors': []}
            
        # Sort colors by frequency
        colors = sorted(colors, key=lambda x: x[0], reverse=True)
        dominant_colors = [f'#{r:02x}{g:02x}{b:02x}' for _, (r,g,b) in colors[:5]]
        
        return {
            'dominant_colors': dominant_colors
        }
        
    def _analyze_hierarchy(self, image: Image.Image) -> list[dict]:
        """Analyze visual hierarchy of elements"""
        width, height = image.size
        
        # Simple hierarchy based on position and size
        hierarchy = [
            {
                'importance': 'high',
                'region': 'top',
                'bbox': (0, 0, width, height//3)
            },
            {
                'importance': 'medium',
                'region': 'middle',
                'bbox': (0, height//3, width, height*2//3)
            },
            {
                'importance': 'low',
                'region': 'bottom',
                'bbox': (0, height*2//3, width, height)
            }
        ]
        return hierarchy


class IntentMatcher:
    """Matches user intent with page content"""
    
    def __init__(self):
        self.intent_patterns = {
            'navigation': ['go to', 'navigate', 'find', 'open'],
            'interaction': ['click', 'type', 'select', 'choose'],
            'extraction': ['get', 'extract', 'read', 'collect'],
            'verification': ['check', 'verify', 'confirm', 'ensure']
        }
        
    def match(self, task: str, semantic_context: dict) -> dict:
        """Match task intent with page content"""
        # Identify primary intent
        primary_intent = self._identify_intent(task)
        
        # Match intent with semantic context
        relevance_score = self._calculate_relevance(
            primary_intent, 
            semantic_context.get('keywords', [])
        )
        
        return {
            'primary_intent': primary_intent,
            'relevance_score': relevance_score,
            'matched_keywords': self._get_matched_keywords(
                task, 
                semantic_context.get('keywords', [])
            )
        }
        
    def _identify_intent(self, task: str) -> str:
        """Identify the primary intent of the task"""
        task_lower = task.lower()
        
        # Check each intent pattern
        for intent, patterns in self.intent_patterns.items():
            if any(pattern in task_lower for pattern in patterns):
                return intent
                
        return 'unknown'
        
    def _calculate_relevance(self, intent: str, keywords: list[str]) -> float:
        """Calculate relevance score between intent and keywords"""
        if not keywords:
            return 0.0
            
        # Get intent-related keywords
        intent_keywords = self.intent_patterns.get(intent, [])
        
        # Calculate overlap
        matches = sum(1 for keyword in keywords if any(
            intent_kw in keyword for intent_kw in intent_keywords
        ))
        
        return matches / len(keywords) if keywords else 0.0
        
    def _get_matched_keywords(self, task: str, keywords: list[str]) -> list[str]:
        """Get keywords that match the task"""
        task_words = set(task.lower().split())
        return [kw for kw in keywords if kw in task_words]


class TaskPlanner:
    """Enhanced task planning and decomposition capabilities"""
    
    def __init__(self):
        self.task_patterns = {
            'navigation': {
                'patterns': ['go to', 'navigate', 'open'],
                'subtasks': ['check current page', 'find target link/url', 'navigate']
            },
            'form_filling': {
                'patterns': ['fill', 'enter', 'input'],
                'subtasks': ['locate form', 'identify fields', 'enter data', 'submit']
            },
            'data_extraction': {
                'patterns': ['extract', 'get', 'collect'],
                'subtasks': ['locate data', 'extract content', 'validate data']
            },
            'interaction': {
                'patterns': ['click', 'select', 'choose'],
                'subtasks': ['find element', 'verify clickable', 'perform action']
            }
        }
        
    def decompose(self, task: str) -> list[str]:
        """Break down complex tasks into subtasks"""
        task_lower = task.lower()
        
        # Identify task type
        task_type = None
        for t_type, info in self.task_patterns.items():
            if any(pattern in task_lower for pattern in info['patterns']):
                task_type = t_type
                break
                
        if not task_type:
            return [task]  # Can't decompose, return original task
            
        # Get subtasks for this task type
        subtasks = self.task_patterns[task_type]['subtasks']
        
        # Add task-specific context to subtasks
        context_words = [w for w in task_lower.split() if len(w) > 3]
        return [f"{subtask} ({' '.join(context_words)})" for subtask in subtasks]
        
    def analyze_dependencies(self, subtasks: list[str]) -> dict:
        """Analyze dependencies between subtasks"""
        dependencies = {}
        
        # Each subtask depends on the previous one
        for i in range(1, len(subtasks)):
            dependencies[subtasks[i]] = [subtasks[i-1]]
            
        return dependencies
        
    def create_execution_plan(self, subtasks: list[str], dependencies: dict) -> list[str]:
        """Create an ordered execution plan based on subtasks and dependencies"""
        # Topological sort for dependency resolution
        visited = set()
        temp_visited = set()
        order = []
        
        def visit(task):
            if task in temp_visited:
                return  # Skip cyclic dependencies
            if task in visited:
                return
                
            temp_visited.add(task)
            
            # Visit dependencies first
            for dep in dependencies.get(task, []):
                visit(dep)
                
            temp_visited.remove(task)
            visited.add(task)
            order.append(task)
            
        for task in subtasks:
            if task not in visited:
                visit(task)
                
        return order


class FusionModule:
    """Combines multiple analysis results for better decision making"""
    
    def combine(self, results: list) -> dict:
        """Combine results from different analyzers"""
        if not results:
            return {}
            
        combined = {
            'text_understanding': results[0] if len(results) > 0 else {},
            'visual_understanding': results[1] if len(results) > 1 else {},
            'layout_understanding': results[2] if len(results) > 2 else {},
        }
        
        # Combine insights
        insights = self._extract_insights(combined)
        confidence = self._calculate_confidence(combined)
        
        return {
            'combined_analysis': combined,
            'insights': insights,
            'confidence': confidence
        }
        
    def _extract_insights(self, combined: dict) -> list[str]:
        """Extract key insights from combined analysis"""
        insights = []
        
        # Add text-based insights
        text_understanding = combined.get('text_understanding', {})
        if text_understanding:
            if 'main_topics' in text_understanding:
                insights.append(f"Main topics: {', '.join(text_understanding['main_topics'])}")
            if 'sentiment' in text_understanding:
                insights.append(f"Content sentiment: {text_understanding['sentiment']}")
                
        # Add visual insights
        visual_understanding = combined.get('visual_understanding', {})
        if visual_understanding:
            if 'layout_regions' in visual_understanding:
                regions = [r['type'] for r in visual_understanding['layout_regions']]
                insights.append(f"Detected regions: {', '.join(regions)}")
            if 'color_scheme' in visual_understanding:
                colors = visual_understanding['color_scheme'].get('dominant_colors', [])
                if colors:
                    insights.append(f"Main colors: {', '.join(colors[:3])}")
                    
        return insights
        
    def _calculate_confidence(self, combined: dict) -> float:
        """Calculate confidence score for the combined analysis"""
        confidence_scores = []
        
        # Check text understanding
        text = combined.get('text_understanding', {})
        if text:
            text_score = (
                0.3 * bool(text.get('keywords')) +
                0.3 * bool(text.get('main_topics')) +
                0.4 * bool(text.get('sentiment'))
            )
            confidence_scores.append(text_score)
            
        # Check visual understanding
        visual = combined.get('visual_understanding', {})
        if visual:
            visual_score = (
                0.4 * bool(visual.get('layout_regions')) +
                0.3 * bool(visual.get('color_scheme')) +
                0.3 * bool(visual.get('visual_hierarchy'))
            )
            confidence_scores.append(visual_score)
            
        # Calculate weighted average
        return sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0


class EnhancedCustomAgent(CustomAgent):
    """Enhanced version of CustomAgent with real-time data storage and human interaction"""
    
    def __init__(
            self,
            task: str,
            llm: BaseChatModel,
            add_infos: str = "",
            browser: Browser | None = None,
            browser_context: BrowserContext | None = None,
            controller: Controller = Controller(),
            use_vision: bool = True,
            save_conversation_path: Optional[str] = None,
            max_failures: int = 5,
            retry_delay: int = 10,
            system_prompt_class: Type[SystemPrompt] = SystemPrompt,
            max_input_tokens: int = 128000,
            validate_output: bool = False,
            include_attributes: list[str] = [
                "title", "type", "name", "role", "tabindex", "aria-label",
                "placeholder", "value", "alt", "aria-expanded",
            ],
            max_error_length: int = 400,
            max_actions_per_step: int = 10,
            tool_call_in_content: bool = True,
            stop_event: Optional[asyncio.Event] = None,
            output_dir: str = "research_output",
            human_interaction: bool = True,
    ):
        super().__init__(
            task=task,
            llm=llm,
            add_infos=add_infos,
            browser=browser,
            browser_context=browser_context,
            controller=controller,
            use_vision=use_vision,
            save_conversation_path=save_conversation_path,
            max_failures=max_failures,
            retry_delay=retry_delay,
            system_prompt_class=system_prompt_class,
            max_input_tokens=max_input_tokens,
            validate_output=validate_output,
            include_attributes=include_attributes,
            max_error_length=max_error_length,
            max_actions_per_step=max_actions_per_step,
            tool_call_in_content=tool_call_in_content,
            stop_event=stop_event,
        )
        
        # Initialize file system agent and data storage
        self.fs_agent = FileSystemAgent(output_dir)
        self.human_interaction = human_interaction
        self.human_queue = asyncio.Queue() if human_interaction else None
        self._initialize_storage()
        
    def _initialize_storage(self):
        """Initialize intelligent data storage"""
        self.current_data = {
            'valuable_data': [],
            'decisions': [],
            'human_interactions': [],
            'insights': [],
            'error_count': 0
        }
        
        # Create session and initial files
        self.fs_agent.create_session()
        self._create_storage_files()
        
    def _create_storage_files(self):
        """Create files for data storage and tracking"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Create real-time status file
        status_content = f"""# Task Execution Status
Started at: {timestamp}
Task: {self.task}

## Current Progress
```
Valuable Data Points: 0
Decisions Made: 0
Human Interactions: 0
Insights Generated: 0
Errors Encountered: 0
```

## Latest Updates
"""
        self.fs_agent.save_content(status_content, 'real_time_status.md')
        
        # Create data storage file
        data_content = {
            "task_info": {
                "start_time": timestamp,
                "task": self.task,
                "status": "in_progress"
            },
            "valuable_data": [],
            "decisions": [],
            "human_interactions": [],
            "insights": []
        }
        self.fs_agent.save_content(data_content, 'data/task_data.json', 'json')
        
    async def ask_human(self, question: str, context: dict = None) -> str:
        """Ask for human input when needed"""
        if not self.human_interaction:
            logger.warning("Human interaction is disabled")
            return None
            
        # Format the question with context
        formatted_question = {
            "question": question,
            "context": context,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Log the interaction
        self.current_data['human_interactions'].append(formatted_question)
        self._update_storage("human_interactions", formatted_question)
        
        # Update status
        self._update_status(f"Waiting for human input: {question}")
        
        # Put question in queue and wait for answer
        await self.human_queue.put(formatted_question)
        return await self.human_queue.get()
        
    def store_valuable_data(self, data: Any, category: str, importance: str = "medium"):
        """Store data deemed valuable by the agent"""
        data_point = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "category": category,
            "importance": importance,
            "data": data
        }
        
        self.current_data['valuable_data'].append(data_point)
        self._update_storage("valuable_data", data_point)
        self._update_status(f"Stored valuable {category} data")
        
    def record_decision(self, decision: str, reasoning: str, confidence: float):
        """Record important decisions made by the agent"""
        decision_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "decision": decision,
            "reasoning": reasoning,
            "confidence": confidence
        }
        
        self.current_data['decisions'].append(decision_data)
        self._update_storage("decisions", decision_data)
        
        if confidence < 0.7 and self.human_interaction:
            asyncio.create_task(self.ask_human(
                f"Low confidence decision ({confidence:.2f}): {decision}\nReasoning: {reasoning}\nShould I proceed?",
                {"decision": decision_data}
            ))
            
    def add_insight(self, insight: str, source: str = "analysis"):
        """Add an insight discovered during task execution"""
        insight_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "insight": insight,
            "source": source
        }
        
        self.current_data['insights'].append(insight_data)
        self._update_storage("insights", insight_data)
        self._update_status(f"New insight from {source}: {insight[:100]}...")
        
    def _update_storage(self, category: str, data: dict):
        """Update storage with new data"""
        try:
            # Read current data
            stored_data = self.fs_agent.read_content('data/task_data.json', 'json')
            if not stored_data:
                stored_data = {
                    "valuable_data": [],
                    "decisions": [],
                    "human_interactions": [],
                    "insights": []
                }
            
            # Update category
            if category not in stored_data:
                stored_data[category] = []
            stored_data[category].append(data)
            
            # Save updated data
            self.fs_agent.save_content(stored_data, 'data/task_data.json', 'json')
            
        except Exception as e:
            logger.error(f"Error updating storage: {str(e)}")
            
    def _update_status(self, message: str, is_error: bool = False):
        """Update status with new information"""
        try:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Read current status
            status_content = self.fs_agent.read_content('real_time_status.md')
            if not status_content:
                self._create_storage_files()
                status_content = self.fs_agent.read_content('real_time_status.md')
            
            # Add new message
            new_message = f"\n{timestamp}: {'❌ ' if is_error else '✅ '}{message}"
            self.fs_agent.append_content(new_message, 'real_time_status.md')
            
            # Update statistics
            stats = f"""```
Valuable Data Points: {len(self.current_data['valuable_data'])}
Decisions Made: {len(self.current_data['decisions'])}
Human Interactions: {len(self.current_data['human_interactions'])}
Insights Generated: {len(self.current_data['insights'])}
Errors Encountered: {self.current_data['error_count']}
```"""
            
            # Replace old stats with new ones
            status_parts = status_content.split("```")
            if len(status_parts) >= 3:
                status_parts[1] = stats
                updated_content = "```".join(status_parts)
                self.fs_agent.save_content(updated_content, 'real_time_status.md')
            
            # Print status to console
            logger.info(f"Status Update: {message}")
            
        except Exception as e:
            logger.error(f"Error updating status: {str(e)}")

    async def run(self, max_steps: int = 100) -> AgentHistoryList:
        """Enhanced run with intelligent data collection and human interaction"""
        try:
            self._update_status(f"Starting task: {self.task}")
            
            # Run the agent
            history = await super().run(max_steps)
            
            # Analyze execution and store insights
            self._analyze_execution(history)
            
            # Update final status
            success = history.is_done()
            self._update_status(
                f"Task {'completed successfully' if success else 'failed'}"
            )
            
            # Create comprehensive summary
            summary = self._create_execution_summary(history)
            self.fs_agent.save_content(summary, 'reports/execution_summary.md')
            
            return history
            
        except Exception as e:
            self._update_status(f"Fatal error: {str(e)}", is_error=True)
            raise
        finally:
            # Compress session
            self.fs_agent.compress_session()
            
    def _analyze_execution(self, history: AgentHistoryList):
        """Analyze execution history for insights"""
        # Analyze steps
        for step in history.history:
            if step.model_output:
                # Extract insights from thought process
                thought = step.model_output.current_state.thought
                if thought:
                    self.add_insight(thought, "thought_process")
                    
                # Analyze actions and results
                if step.result:
                    for result in step.result:
                        if hasattr(result, 'extracted_content') and result.extracted_content:
                            self.store_valuable_data(
                                result.extracted_content,
                                "extracted_data",
                                "high"
                            )
                            
    def _create_execution_summary(self, history: AgentHistoryList) -> str:
        """Create a comprehensive execution summary"""
        summary = []
        summary.append(f"# Task Execution Summary\n")
        summary.append(f"Task: {self.task}\n")
        summary.append(f"Steps Completed: {len(history.history)}\n")
        summary.append(f"Success: {history.is_done()}\n\n")
        
        # Add valuable data summary
        summary.append("## Valuable Data Collected\n")
        for data in self.current_data['valuable_data']:
            summary.append(f"- [{data['importance']}] {data['category']}: {data['data']}\n")
            
        # Add key decisions
        summary.append("\n## Key Decisions\n")
        for decision in self.current_data['decisions']:
            summary.append(f"- Decision: {decision['decision']}\n")
            summary.append(f"  Reasoning: {decision['reasoning']}\n")
            summary.append(f"  Confidence: {decision['confidence']:.2f}\n")
            
        # Add insights
        summary.append("\n## Insights Generated\n")
        for insight in self.current_data['insights']:
            summary.append(f"- [{insight['source']}] {insight['insight']}\n")
            
        # Add human interactions if any
        if self.current_data['human_interactions']:
            summary.append("\n## Human Interactions\n")
            for interaction in self.current_data['human_interactions']:
                summary.append(f"- Q: {interaction['question']}\n")
                if 'answer' in interaction:
                    summary.append(f"  A: {interaction['answer']}\n")
                    
        return "\n".join(summary)
