#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Script to run browser agent tasks directly from the terminal

import asyncio
import argparse
import os
from dotenv import load_dotenv

# Import necessary components
from src.agent.custom_agent import CustomAgent
from src.browser.custom_browser import CustomBrowser
from src.controller.custom_controller import CustomController
from src.agent.custom_prompts import CustomSystemPrompt
from src.utils import utils
from browser_use.browser.browser import BrowserConfig
from browser_use.browser.context import BrowserContextConfig, BrowserContextWindowSize


async def run_task(args):
    # Initialize LLM
    llm = utils.get_llm_model(
        provider=args.llm_provider,
        model_name=args.llm_model_name,
        temperature=args.llm_temperature,
        base_url=args.llm_base_url,
        api_key=args.llm_api_key,
    )

    # Initialize browser
    browser = CustomBrowser(
        config=BrowserConfig(
            headless=args.headless,
            disable_security=args.disable_security,
            chrome_instance_path=args.browser_path,
            extra_chromium_args=[
                f"--window-size={args.window_width},{args.window_height}",
                "--no-first-run",
                "--no-default-browser-check"
            ],
        )
    )

    # Initialize browser context
    browser_context = await browser.new_context(
        config=BrowserContextConfig(
            trace_path=args.save_trace_path if args.enable_recording else None,
            save_recording_path=args.save_recording_path if args.enable_recording else None,
            no_viewport=False,
            browser_window_size=BrowserContextWindowSize(
                width=args.window_width,
                height=args.window_height
            ),
        )
    )

    # Initialize controller
    controller = CustomController()

    # Create stop event for agent control
    stop_event = asyncio.Event()

    try:
        # Create and run agent
        agent = CustomAgent(
            task=args.task,
            add_infos=args.add_infos,
            use_vision=args.use_vision,
            llm=llm,
            browser=browser,
            browser_context=browser_context,
            controller=controller,
            system_prompt_class=CustomSystemPrompt,
            max_actions_per_step=args.max_actions_per_step,
            tool_call_in_content=args.tool_call_in_content,
            stop_event=stop_event
        )

        # Run the agent
        history = await agent.run(max_steps=args.max_steps)

        # Print results
        print("\n\n" + "="*50)
        print("TASK EXECUTION RESULTS")
        print("="*50)
        print(f"Final Result: {history.final_result()}")
        print(f"Errors: {history.errors()}")
        
        # Return final status
        return {
            "success": history.is_done(),
            "final_result": history.final_result(),
            "errors": history.errors()
        }

    finally:
        # Always clean up browser resources if not keeping open
        if not args.keep_browser_open:
            await browser_context.close()
            await browser.close()


def get_browser_path(browser_type):
    """Get the path to the browser executable"""
    import platform
    system = platform.system()
    
    if browser_type == "Chrome":
        if system == "Darwin":  # macOS
            return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        elif system == "Windows":
            import os
            return os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe")
        elif system == "Linux":
            return "/usr/bin/google-chrome"
    elif browser_type == "Arc" and system == "Darwin":
        return "/Applications/Arc.app/Contents/MacOS/Arc"
    
    return None


def main():
    # Load environment variables
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Run browser tasks from the command line")
    
    # Task parameters
    parser.add_argument("--task", type=str, required=True, help="The task to perform")
    parser.add_argument("--add-infos", type=str, default="", help="Additional information for the task")
    parser.add_argument("--max-steps", type=int, default=100, help="Maximum number of steps to execute")
    
    # LLM parameters
    parser.add_argument("--llm-provider", type=str, default="openai", 
                        choices=["openai", "anthropic", "gemini", "deepseek", "ollama", "azure_openai"],
                        help="LLM provider to use")
    parser.add_argument("--llm-model-name", type=str, help="Model name to use")
    parser.add_argument("--llm-temperature", type=float, default=1.0, help="Temperature for the LLM")
    parser.add_argument("--llm-base-url", type=str, help="Base URL for the LLM API")
    parser.add_argument("--llm-api-key", type=str, help="API key for the LLM")
    
    # Browser parameters
    parser.add_argument("--browser-type", type=str, default="Chrome", choices=["Chrome", "Arc"],
                        help="Browser type to use")
    parser.add_argument("--browser-path", type=str, help="Path to browser executable")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--disable-security", action="store_true", help="Disable browser security")
    parser.add_argument("--keep-browser-open", action="store_true", help="Keep browser open after task")
    parser.add_argument("--window-width", type=int, default=1280, help="Browser window width")
    parser.add_argument("--window-height", type=int, default=1100, help="Browser window height")
    
    # Agent parameters
    parser.add_argument("--use-vision", action="store_true", default=True, help="Enable vision capabilities")
    parser.add_argument("--max-actions-per-step", type=int, default=10, 
                        help="Maximum number of actions per step")
    parser.add_argument("--tool-call-in-content", action="store_true", default=True,
                        help="Include tool calls in content")
    
    # Recording parameters
    parser.add_argument("--enable-recording", action="store_true", help="Enable browser recording")
    parser.add_argument("--save-recording-path", type=str, default="./tmp/record_videos",
                        help="Path to save recordings")
    parser.add_argument("--save-trace-path", type=str, default="./tmp/traces",
                        help="Path to save traces")
    
    args = parser.parse_args()
    
    # Use default browser path if not specified
    if not args.browser_path:
        args.browser_path = get_browser_path(args.browser_type)
    
    # Use default model name based on provider if not specified
    if not args.llm_model_name:
        model_defaults = {
            "openai": "gpt-4o",
            "anthropic": "claude-3-5-sonnet-20240620",
            "gemini": "gemini-2.0-flash-exp",
            "deepseek": "deepseek-chat",
            "ollama": "deepseek-r1:latest",
            "azure_openai": "gpt-4o"
        }
        args.llm_model_name = model_defaults.get(args.llm_provider)
    
    # Run the task
    asyncio.run(run_task(args))

if __name__ == "__main__":
    main() 