#!/usr/bin/env python3
"""
Tests for the prompt template database functionality.
"""

import os
import tempfile
import shutil
from server.prompt_template_db import PromptTemplateDatabase, PromptTemplateRepresentation
from server.utils import set_prompt_template, get_latest_prompt_template
from rich.console import Console
from rich.panel import Panel

def test_database_initialization():
    """Test database initialization and basic operations."""
    console = Console()
    console.print(Panel("[bold blue]🧪 Testing database initialization...[/bold blue]", border_style="blue"))
    
    # Test with a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
        temp_file.write('{"AI news": {"1": {"prompt_template": "Test template", "placeholders": {}, "topic": "AI news", "version": 1, "created_at": "2025-08-11T15:31:22.776035", "updated_at": "2025-08-11T15:31:22.776035"}}}')
        temp_file.flush()
        
        try:
            db = PromptTemplateDatabase(temp_file.name)
            console.print("✅ Database loaded successfully with existing templates")
            
            # Test basic operations
            topics = db.list_topics()
            console.print(f"📋 Available topics: {topics}")
            
            # Test getting template info
            template_info = db.get_template_info("AI news")
            console.print(f"📊 AI news template metadata: {template_info}")
            
        finally:
            # Clean up
            os.unlink(temp_file.name)

def test_database_loading():
    """Test loading from existing JSON file."""
    console = Console()
    console.print(Panel("[bold blue]🧪 Testing database loading from JSON file...[/bold blue]", border_style="blue"))
    
    # Test loading from the actual database file
    if os.path.exists("prompt_templates.json"):
        try:
            db = PromptTemplateDatabase("prompt_templates.json")
            
            # Test loading AI news template
            ai_news_template = db.get_latest_template("AI news")
            console.print(f"✅ AI news template loaded successfully")
            console.print(f"   Template length: {len(ai_news_template.prompt_template)}")
            console.print(f"   Placeholders: {ai_news_template.placeholders}")
            
            # Test listing topics
            topics = db.list_topics()
            console.print(f"✅ Available topics: {topics}")
            
        except Exception as e:
            console.print(f"❌ Error loading from database: {e}")
            return False
    else:
        console.print("⚠️  No existing database file found, skipping loading test")
    
    return True

def test_version_management():
    """Test version management functionality."""
    console = Console()
    console.print(Panel("[bold blue]🎯 Testing version management...[/bold blue]", border_style="blue"))
    
    # Test with a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
        temp_file.write('{"AI news": {"1": {"prompt_template": "Test template", "placeholders": {}, "topic": "AI news", "version": 1, "created_at": "2025-08-11T15:31:22.776035", "updated_at": "2025-08-11T15:31:22.776035"}}}')
        temp_file.flush()
        
        try:
            db = PromptTemplateDatabase(temp_file.name)
            
            # Test adding new versions
            db.set_template("research papers", "Analyze {count} research papers on {subject} published between {start_year} and {end_year}. Extract key findings and methodologies.", {
                "count": "int",
                "subject": "str", 
                "start_year": "int",
                "end_year": "int"
            })
            console.print("✅ Added 'research papers' v1")
            
            db.set_template("research papers", "Analyze {count} research papers on {subject} published between {start_year} and {end_year}. Extract key findings and methodologies.", {
                "count": "int",
                "subject": "str", 
                "start_year": "int",
                "end_year": "int"
            })
            console.print("✅ Added 'research papers' v2")
            
            # Test getting latest template (highest version)
            latest_research = db.get_latest_template("research papers")
            console.print(f"✅ Latest research template: v{latest_research.version}")
            
            # Test getting all versions
            all_versions = db.get_all_versions("research papers")
            console.print(f"✅ All versions: {[f'v{t.version}' for t in all_versions]}")
            
            # Test getting specific version
            v1_template = db.get_template("research papers", 1)
            console.print(f"✅ Retrieved v1 template")
            
        finally:
            # Clean up
            os.unlink(temp_file.name)

def test_basic_operations():
    """Test basic database operations."""
    console = Console()
    console.print(Panel("[bold blue]🧪 Testing basic database operations...[/bold blue]", border_style="blue"))
    
    # Test with a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
        temp_file.write('{"AI news": {"1": {"prompt_template": "Test template", "placeholders": {}, "topic": "AI news", "version": 1, "created_at": "2025-08-11T15:31:22.776035", "updated_at": "2025-08-11T15:31:22.776035"}}}')
        temp_file.flush()
        
        try:
            db = PromptTemplateDatabase(temp_file.name)
            
            # Test listing topics
            topics = db.list_topics()
            console.print(f"📋 Available topics: {topics}")
            
            # Test getting template info
            template_info = db.get_template_info("AI news")
            console.print(f"📊 AI news template metadata: {template_info}")
            
            # Test adding new template
            db.set_template("tech news", "Summarize {number} tech articles about {topic} from {start_date} to {end_date}. Focus on {focus_area}.", {
                "number": "int",
                "topic": "str",
                "start_date": "str", 
                "end_date": "str",
                "focus_area": "str"
            })
            console.print("✅ Added new 'tech news' template")
            
            # Test updated topics
            updated_topics = db.list_topics()
            console.print(f"📋 Updated topics: {updated_topics}")
            
            # Test template content
            tech_template = db.get_latest_template("tech news")
            console.print(f"📝 Tech news template: {tech_template.prompt_template}")
            console.print(f"🔧 Placeholders: {tech_template.placeholders}")
            
        finally:
            # Clean up
            os.unlink(temp_file.name)

def test_advanced_operations():
    """Test advanced database operations."""
    console = Console()
    console.print(Panel("[bold blue]🚀 Testing advanced database operations...[/bold blue]", border_style="blue"))
    
    # Test with a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
        temp_file.write('{"AI news": {"1": {"prompt_template": "Test template", "placeholders": {}, "topic": "AI news", "version": 1, "created_at": "2025-08-11T15:31:22.776035", "updated_at": "2025-08-11T15:31:22.776035"}}}')
        temp_file.flush()
        
        try:
            db = PromptTemplateDatabase(temp_file.name)
            
            # Test backup functionality
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = db.db_file.replace('.json', f'_backup_{timestamp}.json')
            shutil.copy2(db.db_file, backup_file)
            console.print(f"💾 Created backup: {os.path.basename(backup_file)}")
            
            # Test adding template through utils
            set_prompt_template("research papers", "Analyze {count} research papers on {subject} published between {start_year} and {end_year}. Extract key findings and methodologies.", {
                "count": "int",
                "subject": "str", 
                "start_year": "int",
                "end_year": "int"
            })
            console.print("✅ Added 'research papers' template")
            
            # Test getting latest template through utils
            latest_template = get_latest_prompt_template("research papers")
            console.print(f"✅ Retrieved latest template: {latest_template.prompt_template[:50]}...")
            
            # Test final state
            final_topics = db.list_topics()
            console.print(f"📋 Final topics: {final_topics}")
            
            # Clean up backup
            os.unlink(backup_file)
            
        finally:
            # Clean up
            os.unlink(temp_file.name)

def test_template_formatting():
    """Test template formatting functionality."""
    console = Console()
    console.print(Panel("[bold blue]🎯 Testing template formatting...[/bold blue]", border_style="blue"))
    
    # Test with a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
        temp_file.write('{"tech news": {"1": {"prompt_template": "Summarize {number} tech articles about {topic} from {start_date} to {end_date}. Focus on {focus_area}.", "placeholders": {"number": "int", "topic": "str", "start_date": "str", "end_date": "str", "focus_area": "str"}, "topic": "tech news", "version": 1, "created_at": "2025-08-11T15:31:22.776035", "updated_at": "2025-08-11T15:31:22.776035"}}}')
        temp_file.flush()
        
        try:
            db = PromptTemplateDatabase(temp_file.name)
            
            # Test template formatting
            template = db.get_latest_template("tech news")
            formatted_prompt = template.prompt_template.format(
                number=5,
                topic="artificial intelligence",
                start_date="2024-01-01",
                end_date="2024-01-31",
                focus_area="machine learning applications"
            )
            
            console.print("📝 Formatted prompt:")
            console.print(formatted_prompt)
            
        finally:
            # Clean up
            os.unlink(temp_file.name)

def main():
    """Run all tests."""
    console = Console()
    console.print(Panel("[bold green]🎬 Starting prompt template database tests...[/bold green]", border_style="green"))
    
    try:
        # Test database initialization
        test_database_initialization()
        
        # Test loading from existing file
        if not test_database_loading():
            console.print("❌ Some tests failed.")
            return
        
        # Test version management
        test_version_management()
        
        # Test basic operations
        test_basic_operations()
        
        # Test advanced operations
        test_advanced_operations()
        
        # Test template formatting
        test_template_formatting()
        
        console.print("\n🎉 All tests completed successfully!")
        
        # Show final database info
        if os.path.exists("prompt_templates.json"):
            console.print(f"📁 Database file: prompt_templates.json")
            db = PromptTemplateDatabase("prompt_templates.json")
            topics = db.list_topics()
            total_templates = sum(len(db.get_all_versions(topic)) for topic in topics)
            console.print(f"📊 Total templates: {total_templates}")
        
    except Exception as e:
        console.print(f"❌ Test failed with error: {e}")
        raise

if __name__ == "__main__":
    main()
