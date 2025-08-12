import re

from datetime import datetime, timedelta
from typing import Optional, Dict

from loguru import logger
from .prompt_template_db import PromptTemplateRepresentation, prompt_db

def render(template_string, variables):
    placeholders = re.findall(r"{([^{}]+)}", template_string)

    result = template_string
    for placeholder in placeholders:
        if placeholder in variables:
            result = result.replace(
                "{" + placeholder + "}", str(variables[placeholder])
            )

    return result.replace("{{", "{").replace("}}", "}")

def ensure_datetime(date_string: str) -> datetime:
    """Parse date string in various formats and return a datetime object."""
    
    match date_string:
        case "today":
            return datetime.now()
        case "yesterday":
            return datetime.now() - timedelta(days=1)
        case "last_week":
            return datetime.now() - timedelta(days=7)
        case "last_month":
            return datetime.now() - timedelta(days=30)
        case "last_year":
            return datetime.now() - timedelta(days=365)
        case _:
            logger.info(f"Parsing date: {date_string}")            
            formats = [
                '%Y-%m-%d',
                '%m/%d/%Y',
                '%d/%m/%Y',
                '%Y-%m-%d %H:%M:%S',
                '%m/%d/%Y %H:%M:%S'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_string, fmt)
                except ValueError:
                    continue
            
            raise ValueError(f"Unable to parse date: {date_string}")




def get_current_prompt(topic: str, start_period: str = "yesterday", end_period: str = "today", number_of_news_items: int = 10, location: str = "San Francisco") -> str:
    """Get the current prompt with placeholders filled in from the database."""
    template = prompt_db.get_best_template(topic)
    return template.prompt_template.format(
        start_period=start_period,
        end_period=end_period,
        topic=topic,
        number_of_news_items=number_of_news_items,
        location=location
    )

def get_best_prompt_template(topic: str) -> PromptTemplateRepresentation:
    """Retrieve the prompt template for the topic from the database."""
    return prompt_db.get_best_template(topic)
    

def set_prompt_template(topic: str, score: float, prompt: str, placeholders: Optional[Dict[str, str]] = None):
    """Set the prompt template for the topic in the database."""
    prompt_db.set_template(topic, score, prompt, placeholders)
    prompt_db.save()

