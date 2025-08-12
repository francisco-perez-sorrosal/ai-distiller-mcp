import sys
import shutil
from tkinter import Frame
from typing import List

from pydantic import BaseModel, Field
import typer
import dspy

from pathlib import Path
from mcp.server.fastmcp import FastMCP
from loguru import logger
from rich import console
from rich.rule import Rule
import mcp.types as types

from server.dataset_generator import DatasetGenerator
from server.gmail import GmailAPIClient, emails_to_json
from server.prompt_curator import PromptCurator
from server.utils import ensure_datetime, get_best_prompt_template, set_prompt_template

# Initialize server
mcp = FastMCP("ai-news-distiller-mcp")

# dspy
lm = dspy.LM("anthropic/claude-3-5-haiku-20241022")

# Dummy feedback storage TODO: Implement a proper feedback storage in OxenAI
feedback = {}


logger.info("Initializing Gmail client. Current directory: {os.getcwd()}")
gmail_client = GmailAPIClient(credentials_file="credentials.json")


beautiful_console = console.Console()

class Email(BaseModel):
    title: str = Field(description="Email title")
    sender: str = Field(description="Email sender")
    date: str = Field(description="Email date in YYYY-MM-DD HH:MM:SSformat")
    content: str = Field(description="Email content")

class ReviewEmails(dspy.Signature):
    """Review the emails passed and select the ones that are interesting for the topic at hand"""
    emails: List[str] = dspy.InputField(description="List of emails to review")
    topic: str = dspy.InputField(description="Topic to review the emails for")
    period: str = dspy.InputField(description="Period to review the emails for")
    # Output
    selected_emails: List[Email] = dspy.OutputField(description="List of emails that are interesting for the topic at hand")


class Distiller(dspy.Module):
    def __init__(self):
        super().__init__()
        self.review_emails = dspy.ChainOfThought(ReviewEmails)
    
    def forward(self, emails: List[str], topic: str, period: str) -> str:
        """Process emails through the review pipeline to extract relevant content.
        
        Args:
            emails (List[str]): List of email content strings to process.
                Each email should be a string containing the email body text.
            topic (str): The topic or theme to filter emails by.
                Examples: "AI news", "tech updates", "industry insights".
            period (str): The time period context for the emails.
                Examples: "current week", "last month", "Q1 2024".
        
        Returns:
            str: A concatenated string of selected emails in JSON format.
                Only emails relevant to the specified topic are included.
                Each email is formatted as a JSON string with title, sender, date, and content.
        
        Raises:
            Exception: If there's an error in the email review process.
        
        Example:
            >>> distiller = Distiller()
            >>> result = distiller.forward(["email1", "email2"], "AI news", "this week")
        """
        logger.info(f"Calling review_emails with {emails}, {topic}, {period}")
        result = self.review_emails(emails=emails, topic=topic, period=period)
        logger.info("--------------------------------")
        logger.info(type(result))
        logger.info(result)
        logger.info("--------------------------------")
        
        selected_emails_content = result.selected_emails
        
        logger.info(f"News digest type: {type(selected_emails_content)}")
        logger.info(f"News digest content: {selected_emails_content}")
        
        string_emails = [email.model_dump_json(indent=2) for email in selected_emails_content]
        
        return " ".join(string_emails)

# @mcp.tool()
# def distill_news(emails: List[str], topic: str = "AI news", period: str = "current week") -> str:
#     """Retrieve the list of emails from the period specified and filter only those that are relevant to the topic"""
#     distiller = Distiller()
#     result = distiller(emails=emails, topic=topic, period=period)
#     return result


@mcp.tool()
def create_dataset(num_cases: int = 3):
    """For test purposes only, allow invoke from here"""
    
    goal = """Generate a comprehensive prompt template for a news digest by analyzing Gmail 
    newsletters within a specified timeframe to extract and organize 
    topic-specific news items with detailed metadata and possible local events."""
    
    prompt_inputs_spec={
        "start_period": "Beginning date/timeframe for email analysis - defines the lower bound of the search window",
        "end_period": "Ending date/timeframe for email analysis - defines the upper bound of the search window", 
        "topic": "Subject matter focus for filtering newsletters and news items (e.g., 'AI news', 'tech', 'blockchain')",
        "number_of_news_items": "Maximum quantity of news items to include in the final digest output",
        "location": "Geographic area for filtering relevant local events to include in the events section"
    }
    
    dataset_generator = DatasetGenerator(task_description=goal, prompt_inputs_spec=prompt_inputs_spec, filename="dataset.json")
    dataset_file = dataset_generator.run(num_cases=num_cases)
    return f"Dataset created successfully in {dataset_file}"

@mcp.tool()
def get_user_profile() -> str:
    """Retrieve the authenticated user's Gmail profile information.
    
    Returns:
        str: Formatted string containing user profile details including:
            - Email address
            - Total number of messages in the account
            - Authentication status
    
    Raises:
        Exception: If there's an error retrieving the user profile from Gmail API.
    
    Example:
        >>> get_user_profile()
        "👤 Authenticated as: user@example.com\n📧 Total messages in account: 15420"
    """
    profile = gmail_client.get_user_profile()
    if profile:
        return f"👤 Authenticated as: {profile.get('email')}\n📧 Total messages in account: {profile.get('messages_total', 'Unknown')}"
    else:
        return "❌ Error getting profile"


@mcp.tool()
def curate_current_prompt(topic: str) -> str:
    """Retrieve the user feedback stored in the database and curate the current prompt based on it"""
    prompt_curator = PromptCurator()
    
    # 1. Get the best prompt for the topic at hand
    best_prompt_template_representation = get_best_prompt_template(topic)
    beautiful_console.print(Rule(f"Best prompt template:\n{best_prompt_template_representation}"))
    # 2. Get the current feedback
    feedback_string = "\n".join([f"{key}: {value}" for key, value in feedback.items()])
    beautiful_console.print(Rule(f"Current feedback:\n{feedback_string}"))
    # 3. Curate the prompt
    curated_prompt = prompt_curator.forward(prompt=best_prompt_template_representation.prompt_template, feedback=feedback_string)
    beautiful_console.print(Rule(f"Curated prompt:\n{curated_prompt}"))
    # 4. Evaluate the result
    # TODO: Implement the evaluation logic
    # TODO: Implement the update logic
    # 5. If the evaluated result is better than the best prompt, update the best prompt
    if curated_prompt != best_prompt_template_representation:
        beautiful_console.print(Rule(f"Updating best prompt template for topic {topic}"))
        # TODO: Update the best prompt template in the database/filesystem
        set_prompt_template(topic, 0.0, curated_prompt, {})
        
        
    return curated_prompt


@mcp.tool()
def provide_feedback(strengths: str, weaknesses: str, suggestions: str) -> str:
    """Accept the user-provided feedback and classify it into strengths, weaknesses, and suggestions.
    
    Args:
        strengths (str): The strengths of the news digest.
        weaknesses (str): The weaknesses of the news digest.
        suggestions (str): The suggestions for improving the news digest.
    """
    # TODO Save feedback to the database
    # TODO Trigger the prompt update if necessary
    global feedback
    feedback = {
        "strengths": feedback.get("strengths", "") + strengths,
        "weaknesses": feedback.get("weaknesses", "") + weaknesses,
        "suggestions": feedback.get("suggestions", "") + suggestions
    }
    return "Thank you for the feedback! We will use it to improve your future news digest."

@mcp.tool()
def get_emails(start_date: str = "yesterday", end_date: str = "today", max_emails: int = 3) -> str:
    """Get emails from the specified date range.
    
    Args:
        start_date (str): Start date for email retrieval. 
            Accepts absolute dates in "YYYY-MM-DD" format or relative 
            days (just "today" and "yesterday"). Defaults to "yesterday".
        end_date (str): End date for email retrieval.
            Accepts absolute dates in "YYYY-MM-DD" format or relative 
            days (just "today" and "yesterday"). Defaults to "today".    
        max_emails (int): Maximum number of emails to retrieve.
            Must be a positive integer. Defaults to 3.
    
    Returns:
        str: JSON string containing email data with basic information including
            sender, subject, date, and content preview.
    
    Raises:
        ValueError: If max_emails is not a positive integer.
        Exception: If there's an error retrieving emails from Gmail.
    
    Example:
        >>> get_emails("yesterday", "today", 5)
        >>> get_emails("2024-01-01", "2024-01-07", 10)
    """
    start_datetime = ensure_datetime(start_date)
    end_datetime = ensure_datetime(end_date)
    emails = gmail_client.get_emails_by_date_range(start_datetime, end_datetime, basic_data=False, include_body=True, max_results=max_emails)
    return emails_to_json(emails)

################################################################################
# Main tool/prompt
################################################################################


@mcp.tool()
def distill_news(topic: str = "AI news", start_period: str = "yesterday", end_period: str = "today", number_of_emails: int = 3, number_of_news_items: int = 5) -> str:   
    """Generate instructions for LLM to distill news from emails based on user preferences.
    
    Args:
        topic (str): The topic or theme to focus on when distilling news.
            Examples: "AI news", "tech updates", "industry insights".
            Defaults to "AI news".
        start_period (str): Start date for the news distillation period.
            Accepts relative dates like "yesterday", "3 days ago", "last week",
            or absolute dates in "YYYY-MM-DD" format. Defaults to "yesterday".
        end_period (str): End date for the news distillation period.
            Accepts relative dates like "today", "3 days ago", "last week",
            or absolute dates in "YYYY-MM-DD" format. Defaults to "today".
        number_of_emails (int): Number of emails to retrieve and analyze.
            Must be a positive integer. Defaults to 3.
        number_of_news_items (int): Target number of news items to extract.
            Must be a positive integer. Defaults to 3.
    
    Returns:
        str: Structured prompt containing instructions for the LLM to:
            1. Retrieve emails using the get_emails tool
            2. Apply topic-specific distillation using get_prompt
            3. Take into account the user feedback (if any)
            4. Request user feedback and store it
    
    Raises:
        ValueError: If number_of_emails or number_of_news_items are not positive integers.
        Exception: If there's an error generating the distillation instructions.
    
    Example:
        >>> distill_news("AI research", "last week", "today", 5, 15)
        >>> distill_news("tech updates", "2024-01-01", "2024-01-07", 10, 20)
    """
    structured_prompt = f"""Follow this instructions to distill the news about this topic <topic>{topic}</topic> for the user:
    1. Get user {number_of_emails} emails for the period specified using the get_emails tool
    2. {get_prompt(topic, start_period, end_period, number_of_emails, number_of_news_items)}
    3. Before crafting the user response, take into account the following user feedback (if any):
        <feedback>{feedback}</feedback>
    4. Finally, ask for more feedback to the user about the news digest, and register it using the provide_feedback tool.
    Do not come with an update of the information right away. Just thank the user for the
    feedback if necessary or wait for the user to explicitly ask for it."""
    return structured_prompt


@mcp.prompt()
def get_prompt(topic: str, start_period: str = "yesterday", end_period: str = "today", number_of_news_items: int = 5, location: str = "San Francisco") -> str:
    """Retrieve the optimal prompt for news distillation based on topic and context.
    
    Args:
        topic (str): The topic or theme for news distillation.
            Examples: "AI news", "tech updates", "industry insights".
            Used to select topic-specific prompt templates.
        start_period (str): Start date for the news period.
            Accepts absolute dates in "YYYY-MM-DD" format or relative days (just "today" and "yesterday"). Defaults to "yesterday".
        end_period (str): End date for the news period.
            Accepts absolute dates in "YYYY-MM-DD" format or relative days (just "today" and "yesterday"). Defaults to "today".
        number_of_news_items (int): Number of news items to be included in the digest.
            Used to adjust prompt complexity and output expectations.
            Must be a positive integer. Defaults to 5.
        location (str): Geographic location context for news relevance.
            Examples: "San Francisco", "New York", "London".
            Used to tailor location-specific news insights. Defaults to "San Francisco".
    
    Returns:
        str: Curated prompt template optimized for the given topic and context.
            The prompt is retrieved from a database/filesystem and may be
            updated based on user feedback to improve distillation quality.
    
    Raises:
        Exception: If there's an error retrieving the prompt from storage.
        ValueError: If number_emails is not a positive integer.
    
    Note:
        This function retrieves prompts that are continuously curated and improved
        based on user feedback to ensure optimal news distillation results.
    
    Example:
        >>> get_prompt("AI research", "last week", "today", 3, "San Francisco")
        >>> get_prompt("tech updates", "2024-01-01", "2024-01-07", 5, "New York")
    """
    prompt_template = get_best_prompt_template(topic)
    prompt = prompt_template.prompt_template.format(
        start_period=start_period,
        end_period=end_period,
        topic=topic,
        number_of_news_items=number_of_news_items,
        location=location
    )
    logger.info(f"Retrieved prompt template for topic {prompt_template.topic} (v. {prompt_template.version})")
    return prompt


def main(debug: bool = False):
    """Initialize and run the AI News Distiller MCP Server.
    
    Args:
        debug (bool): Enable debug mode for additional logging and verbose output.
            Defaults to False.
    """
    dspy.configure(lm=lm)

    try:
        logger.info("Starting AI News Distiller MCP Server...")
        mcp.run()
    except KeyboardInterrupt:
        logger.warning("Ctrl+C caught! Exiting...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Exception {e}")
        sys.exit(1)


if __name__ == "__main__":
    typer.run(main)
