from fastapi import status


class PromptException(Exception):
    def __init__(self, message: str | None = None):
        self.message = message
        super().__init__(message)


class PromptHTTPException(PromptException):
    def __init__(self, message: str | None = None, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.status_code = status_code
        super().__init__(message)


class DisabledBlockExecutionError(PromptHTTPException):
    def __init__(self, message: str | None = None):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST)


class InvalidOpenAIResponseFormat(PromptException):
    def __init__(self, message: str | None = None):
        super().__init__(f"Invalid response format: {message}")


class TaskNotFound(PromptHTTPException):
    def __init__(self, task_id: str | None = None):
        super().__init__(f"Task {task_id} not found", status_code=status.HTTP_404_NOT_FOUND)


class ScriptNotFound(PromptException):
    def __init__(self, script_name: str | None = None):
        super().__init__(f"Script {script_name} not found. Has the script been registered?")


class MissingElement(PromptException):
    def __init__(self, selector: str | None = None, element_id: str | None = None):
        super().__init__(
            f"Found no elements. Might be due to previous actions which removed this element."
            f" selector={selector} element_id={element_id}",
        )


class MultipleElementsFound(PromptException):
    def __init__(self, num: int, selector: str | None = None, element_id: str | None = None):
        super().__init__(
            f"Found {num} elements. Expected 1. num_elements={num} selector={selector} element_id={element_id}",
        )


class MissingBrowserState(PromptException):
    def __init__(self, task_id: str | None = None, workflow_run_id: str | None = None) -> None:
        task_str = f"task_id={task_id}" if task_id else ""
        workflow_run_str = f"workflow_run_id={workflow_run_id}" if workflow_run_id else ""
        super().__init__(f"Browser state for {task_str} {workflow_run_str} is missing.")


class MissingBrowserStatePage(PromptException):
    def __init__(self, task_id: str | None = None, workflow_run_id: str | None = None):
        task_str = f"task_id={task_id}" if task_id else ""
        workflow_run_str = f"workflow_run_id={workflow_run_id}" if workflow_run_id else ""
        super().__init__(f"Browser state page is missing. {task_str} {workflow_run_str}")


class FailedToNavigateToUrl(PromptException):
    def __init__(self, url: str, error_message: str) -> None:
        self.url = url
        self.error_message = error_message
        super().__init__(f"Failed to navigate to url {url}. Error message: {error_message}")


class FailedToReloadPage(PromptException):
    def __init__(self, url: str, error_message: str) -> None:
        self.url = url
        self.error_message = error_message
        super().__init__(f"Failed to reload page url {url}. Error message: {error_message}")


class UnexpectedTaskStatus(PromptException):
    def __init__(self, task_id: str, status: str) -> None:
        super().__init__(f"Unexpected task status {status} for task {task_id}")


class DisabledFeature(PromptException):
    def __init__(self, feature: str) -> None:
        super().__init__(f"Feature {feature} is disabled")


class UnknownBrowserType(PromptException):
    def __init__(self, browser_type: str) -> None:
        super().__init__(f"Unknown browser type {browser_type}")


class UnknownErrorWhileCreatingBrowserContext(PromptException):
    def __init__(self, browser_type: str, exception: Exception) -> None:
        super().__init__(
            f"Unknown error while creating browser context for {browser_type}. Exception type: {type(exception)} Exception message: {str(exception)}"
        )


class BrowserStateMissingPage(PromptException):
    def __init__(self) -> None:
        super().__init__("BrowserState is missing the main page")


class FailedToTakeScreenshot(PromptException):
    def __init__(self, error_message: str) -> None:
        super().__init__(f"Failed to take screenshot. Error message: {error_message}")


class EmptyScrapePage(PromptException):
    def __init__(self) -> None:
        super().__init__("Failed to scrape the page, returned an NONE result")


class TaskAlreadyCanceled(PromptHTTPException):
    def __init__(self, new_status: str, task_id: str):
        super().__init__(
            f"Invalid task status transition to {new_status} for {task_id} because task is already canceled"
        )


class InvalidTaskStatusTransition(PromptHTTPException):
    def __init__(self, old_status: str, new_status: str, task_id: str):
        super().__init__(f"Invalid task status transition from {old_status} to {new_status} for {task_id}")


class HttpException(PromptException):
    def __init__(self, status_code: int, url: str, msg: str | None = None) -> None:
        super().__init__(f"HTTP Exception, status_code={status_code}, url={url}" + (f", msg={msg}" if msg else ""))


class InvalidUrl(PromptHTTPException):
    def __init__(self, url: str) -> None:
        super().__init__(f"Invalid URL: {url}. 100xprompt supports HTTP and HTTPS urls with max 2083 character length.")


class UnsupportedTaskType(PromptException):
    def __init__(self, task_type: str):
        super().__init__(f"Not supported task type [{task_type}]") 