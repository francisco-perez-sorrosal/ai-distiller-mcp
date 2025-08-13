import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from loguru import logger


class PromptTemplateRepresentation(BaseModel):
    """Represents a prompt template with its metadata and placeholders."""
    topic: str = Field(description="The topic this template is designed for")
    version: int = Field(default=1, description="Version number of this template")
    prompt_template: str = Field(description="The actual prompt template string")
    placeholders: Dict[str, str] = Field(
        description="Dictionary mapping placeholder names to their Python type annotations",
        default_factory=dict
    )
    created_at: datetime = Field(default_factory=datetime.now, description="When this template was created")
    updated_at: datetime = Field(default_factory=datetime.now, description="When this template was last updated")


class PromptTemplateDatabase:
    """Mini-database for storing prompt templates in the filesystem."""
    
    def __init__(self, db_file: str = "prompt_templates.json"):
        self.db_file = db_file
        # New structure: Dict[str, Dict[int, PromptTemplateRepresentation]]
        # topic -> {version -> template}
        self.templates: Dict[str, Dict[int, PromptTemplateRepresentation]] = {}
        try:
            self._load_templates()
        except (FileNotFoundError, Exception) as e:
            # Initialize with empty templates - database file must exist
            self.templates = {}
            logger.warning(f"Warning: {e}")
            logger.warning("Please ensure the prompt templates database file exists and contains valid data.")
    
    def _load_templates(self):
        """Load templates from the filesystem database."""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Load new format
                    for topic, versions_data in data.items():
                        self.templates[topic] = {}
                        for version_str, template_data in versions_data.items():
                            version = int(version_str)
                            # Convert string dates back to datetime objects
                            if 'created_at' in template_data:
                                template_data['created_at'] = datetime.fromisoformat(template_data['created_at'])
                            if 'updated_at' in template_data:
                                template_data['updated_at'] = datetime.fromisoformat(template_data['updated_at'])
                            
                            # Ensure topic is set
                            if 'topic' not in template_data:
                                template_data['topic'] = topic
                            
                            # Create template
                            template = PromptTemplateRepresentation(**template_data)
                            self.templates[topic][version] = template
                        
            except (json.JSONDecodeError, KeyError) as e:
                raise Exception(f"Failed to load prompt templates from {self.db_file}: {e}. Please ensure the file contains valid JSON data.")
        else:
            raise FileNotFoundError(f"Prompt templates database file not found: {self.db_file}. Please create the database file or run the application to initialize it.")
    

    
    def save(self):
        """Save templates to the filesystem database."""
        try:
            # Convert datetime objects to ISO format strings for JSON serialization
            data = {}
            for topic, versions in self.templates.items():
                data[topic] = {}
                for version, template in versions.items():
                    template_dict = template.model_dump()
                    template_dict['created_at'] = template.created_at.isoformat()
                    template_dict['updated_at'] = template.updated_at.isoformat()
                    data[topic][str(version)] = template_dict
            
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving prompt templates: {e}")
    
    def get_latest_template(self, topic: str) -> PromptTemplateRepresentation:
        """Get the latest prompt template for a given topic (highest version)."""
        if not self.templates:
            raise Exception("No prompt templates available. Please ensure the prompt templates database file exists and contains valid data.")
        
        # Check if topic exists
        if topic not in self.templates:
            # Try to get AI news as fallback
            if "AI news" in self.templates:
                fallback_versions = self.templates["AI news"]
                if fallback_versions:
                    latest_fallback = max(fallback_versions.values(), key=lambda t: t.version)
                    return latest_fallback
            raise Exception(f"No prompt template found for topic '{topic}' and no fallback 'AI news' template available.")
        
        # Get all versions for the topic
        topic_versions = self.templates[topic]
        if not topic_versions:
            raise Exception(f"No versions found for topic '{topic}'")
        
        # Return the template with the highest version
        latest_template = max(topic_versions.values(), key=lambda t: t.version)
        return latest_template
    
    def set_template(self, topic: str, prompt_template: str, placeholders: Optional[Dict[str, str]] = None):
        """Set or create a prompt template for a topic."""
        # Initialize topic dict if not exists
        if topic not in self.templates:
            self.templates[topic] = {}
        
        # Find existing templates for this topic
        existing_versions = self.templates[topic]
        
        if existing_versions:
            # Find the highest version number
            max_version = max(existing_versions.keys())
            new_version = max_version + 1
        else:
            new_version = 1
        
        # Create new template with new version
        new_template = PromptTemplateRepresentation(
            prompt_template=prompt_template,
            placeholders=placeholders or {},
            topic=topic,
            version=new_version
        )
        
        # Store in nested structure
        self.templates[topic][new_version] = new_template
        
        self.save()
    
    def delete_template(self, topic: str, version: Optional[int] = None) -> bool:
        """Delete a prompt template for a topic.
        
        Args:
            topic: The topic to delete
            version: Specific version to delete. If None, deletes all versions.
        """
        if topic == "AI news":
            return False  # Prevent deletion of default template
        
        if topic not in self.templates:
            return False
        
        if version is not None:
            # Delete specific version
            if version in self.templates[topic]:
                del self.templates[topic][version]
                # Remove topic if no versions left
                if not self.templates[topic]:
                    del self.templates[topic]
                self.save()
                return True
            return False
        else:
            # Delete all versions of the topic
            del self.templates[topic]
            self.save()
            return True
    
    def list_topics(self) -> list[str]:
        """List all available topics."""
        if not self.templates:
            raise Exception("No prompt templates available. Please ensure the prompt templates database file exists and contains valid data.")
        # Return topic keys directly
        return list(self.templates.keys())
    
    def get_template_info(self, topic: str) -> Optional[Dict[str, Any]]:
        """Get metadata about the latest template for a topic without the full content."""
        if not self.templates:
            raise Exception("No prompt templates available. Please ensure the prompt templates database file exists and contains valid data.")
        
        # Get the latest template by version
        latest_template = self.get_latest_template(topic)
        
        return {
            "topic": latest_template.topic,
            "version": latest_template.version,
            "created_at": latest_template.created_at,
            "updated_at": latest_template.updated_at,
            "placeholders": latest_template.placeholders,
            "template_length": len(latest_template.prompt_template)
        }
    
    def get_all_versions(self, topic: str) -> list[PromptTemplateRepresentation]:
        """Get all versions of templates for a specific topic."""
        if not self.templates:
            raise Exception("No prompt templates available. Please ensure the prompt templates database file exists and contains valid data.")
        
        if topic not in self.templates:
            return []
        
        topic_versions = self.templates[topic]
        # Return sorted list of templates by version (descending)
        return sorted(topic_versions.values(), key=lambda t: t.version, reverse=True)
    
    def get_template(self, topic: str, version: int) -> Optional[PromptTemplateRepresentation]:
        """Get a specific version of a template for a topic."""
        if not self.templates:
            raise Exception("No prompt templates available. Please ensure the prompt templates database file exists and contains valid data.")
        
        if topic not in self.templates:
            return None
        
        topic_versions = self.templates[topic]
        return topic_versions.get(version)
    
    def get_current_version(self, topic: str) -> Optional[int]:
        """Get the current (highest) version number for a topic."""
        if not self.templates or topic not in self.templates:
            return None
        
        topic_versions = self.templates[topic]
        if not topic_versions:
            return None
        
        return max(topic_versions.keys())
    
    def get_current_template(self, topic: str) -> Optional[PromptTemplateRepresentation]:
        """Get the current (highest version) template for a topic."""
        current_version = self.get_current_version(topic)
        if current_version is None:
            return None
        
        return self.get_template(topic, current_version)
    
    def update_template_version(self, topic: str, version: int, **updates) -> bool:
        """Update a specific version of a template.
        
        Args:
            topic: The topic of the template
            version: The version to update
            **updates: Fields to update (prompt_template, placeholders, etc.)
        
        Returns:
            True if update was successful, False otherwise
        """
        if not self.templates or topic not in self.templates:
            return False
        
        topic_versions = self.templates[topic]
        if version not in topic_versions:
            return False
        
        template = topic_versions[version]
        
        # Update fields
        for field, value in updates.items():
            if hasattr(template, field):
                setattr(template, field, value)
        
        # Update timestamp
        template.updated_at = datetime.now()
        
        self.save()
        return True


# Initialize the database instance
prompt_db = PromptTemplateDatabase()
