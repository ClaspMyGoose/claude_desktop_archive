#!/usr/bin/env python3
"""
Claude Desktop Archiver for macOS
Automatically archives conversations from the Claude desktop app using Accessibility APIs
"""

import os
import sys
import time
import json
import hashlib
from datetime import datetime
from pathlib import Path
import threading
import queue
import signal
from ApplicationServices import AXUIElementCopyAttributeNames

try:
    import Quartz
    from Cocoa import NSWorkspace, NSRunningApplication
    from PyObjCTools import AppHelper
    from ApplicationServices import AXIsProcessTrusted, AXUIElementCreateApplication, AXUIElementCopyAttributeValue
    from ApplicationServices import kAXWindowsAttribute, kAXValueAttribute, kAXTitleAttribute, kAXChildrenAttribute
except ImportError:
    print("Error: PyObjC not installed. Install with: pip install pyobjc")
    sys.exit(1)


class ClaudeArchiver:
    def __init__(self, save_directory="~/test_archive"):
        self.save_directory = Path(save_directory).expanduser()
        self.save_directory.mkdir(exist_ok=True)
        
        self.claude_app = None
        self.last_conversation_hash = None
        self.monitoring = False
        self.save_queue = queue.Queue()
        
        # Settings
        self.check_interval = 10  # seconds
        self.min_message_length = 1
        self.auto_save_enabled = True
        
        print(f"Save directory: {self.save_directory}")
        
    def check_accessibility_permissions(self):
        """Check if the app has accessibility permissions"""
        trusted = AXIsProcessTrusted()
        if not trusted:
            print("Accessibility permissions required!")
            print("Go to: System Preferences → Security & Privacy → Privacy → Accessibility")
            print("Add Python or your terminal app to the list")
            return False
        print("Accessibility permissions granted")
        return True
        
    def find_claude_app(self):
        """Find the Claude desktop application"""
        workspace = NSWorkspace.sharedWorkspace()
        running_apps = workspace.runningApplications()
        

        print("All running apps:")

        for app in running_apps:
            app_name = app.localizedName()
            if app_name and "claude" in app_name.lower():
                print(f"Found Claude app: {app_name}")
                print(f'Active: {app.isActive()}')
                return app
                
        return None
        
    def get_claude_window_content(self):
        """Extract conversation content from Claude window using Accessibility API"""
        if not self.claude_app:
            return None
            
        try:
            # Get the application's accessibility object
            pid = self.claude_app.processIdentifier()
            app_ref = AXUIElementCreateApplication(pid)
            
            # Get all windows
            windows = AXUIElementCopyAttributeValue(app_ref, kAXWindowsAttribute, None)[1]
            
            if not windows:
                return None
                
            # Use the first (main) window
            main_window = windows[0]
            
            # Try to get all text content from the window
            content = self._extract_text_from_element(main_window)

            print(f"📱 Found {len(windows)} windows")
            content = self._extract_text_from_element(main_window)
            print(f"📝 Extracted content: {len(content) if content else 0} items")
            
            return content
            
        except Exception as e:
            print(f"Error accessing Claude window: {e}")
            return None



    # * OG       
    # def _extract_text_from_element(self, element):
    #     """Recursively extract text from accessibility element"""
    #     text_content = []
        
    #     try:
    #         # Try to get text value directly
    #         text_value = AXUIElementCopyAttributeValue(element, kAXValueAttribute, None)[1]
    #         if text_value and isinstance(text_value, str) and len(text_value.strip()) > 0:
    #             text_content.append(text_value.strip())
                
    #     except:
    #         pass
            
    #     try:
    #         # Try to get title
    #         title = AXUIElementCopyAttributeValue(element, kAXTitleAttribute, None)[1]
    #         if title and isinstance(title, str) and len(title.strip()) > 0:
    #             text_content.append(title.strip())
                
    #     except:
    #         pass
            
    #     try:
    #         # Get children and recurse
    #         children = AXUIElementCopyAttributeValue(element, kAXChildrenAttribute, None)[1]
    #         if children:
    #             for child in children:
    #                 child_text = self._extract_text_from_element(child)
    #                 if child_text:
    #                     text_content.extend(child_text)
                        
    #     except:
    #         pass
            
    #     return text_content

    def _extract_text_from_element(self, element, depth=0):
        """Recursively extract text from accessibility element with comprehensive debugging"""
        text_content = []
        indent = "  " * depth
        
        if depth > 4:  # Don't go too deep
            return text_content
        
        try:
            # Get all available attributes for this element
            attributes = AXUIElementCopyAttributeNames(element, None)[1]
            
            if depth < 2:  # Only show detailed info for top levels
                print(f"{indent}Available attributes: {attributes}")
            
            # Try multiple text-related attributes
            text_attributes = [
                'AXValue', 'AXTitle', 'AXDescription', 'AXHelp', 
                'AXRoleDescription', 'AXPlaceholderValue', 'AXStringForRange',
                'AXAttributedStringForRange', 'AXSelectedText', 'AXVisibleCharacterRange'
            ]
            
            for attr in text_attributes:
                if attr in attributes:
                    try:
                        value = AXUIElementCopyAttributeValue(element, attr, None)[1]
                        if value and isinstance(value, str) and len(value.strip()) > 5:
                            print(f"{indent}✅ Found text in {attr}: {value[:100]}...")
                            text_content.append(value.strip())
                    except Exception as e:
                        if depth < 2:
                            print(f"{indent}❌ Error reading {attr}: {e}")
            
            # Get role for context
            try:
                role = AXUIElementCopyAttributeValue(element, 'AXRole', None)[1]
                if depth < 2:
                    print(f"{indent}Role: {role}")
            except:
                pass
                
        except Exception as e:
            print(f"{indent}Error getting attributes: {e}")
        
        # Recurse through children
        try:
            children = AXUIElementCopyAttributeValue(element, 'AXChildren', None)[1]
            if children and depth < 3:
                print(f"{indent}Checking {len(children)} children...")
                for child in children:
                    child_text = self._extract_text_from_element(child, depth + 1)
                    if child_text:
                        text_content.extend(child_text)
        except:
            pass
        
        return text_content
        
    def process_conversation_content(self, raw_content):
        """Process and structure the raw conversation content"""
        if not raw_content:
            return None
            
        # Join all text content
        full_text = "\n".join(raw_content)
        
        # Basic filtering
        if len(full_text.strip()) < self.min_message_length:
            return None
            
        # Create conversation structure
        conversation = {
            "timestamp": datetime.now().isoformat(),
            "app_name": "Claude Desktop",
            "raw_content": raw_content,
            "processed_text": full_text,
            "message_count": len([line for line in raw_content if len(line.strip()) > 20])
        }
        
        return conversation
        
    def generate_conversation_hash(self, conversation):
        """Generate hash to detect conversation changes"""
        if not conversation:
            return None
            
        content_str = conversation.get("processed_text", "")
        return hashlib.md5(content_str.encode()).hexdigest()
        
    def save_conversation(self, conversation):
        """Save conversation to file"""
        if not conversation:
            return
            
        timestamp = datetime.now()
        filename = f"claude_conversation_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.save_directory / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(conversation, f, indent=2, ensure_ascii=False)
                
            print(f"Saved conversation: {filename}")
            
            # Also save as markdown for easy reading
            md_filename = filename.replace('.json', '.md')
            md_filepath = self.save_directory / md_filename
            self.save_as_markdown(conversation, md_filepath)
            
        except Exception as e:
            print(f"Error saving conversation: {e}")
            
    def save_as_markdown(self, conversation, filepath):
        """Save conversation in markdown format"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# Claude Conversation\n\n")
                f.write(f"**Date:** {conversation['timestamp']}\n\n")
                f.write(f"**Messages:** {conversation['message_count']}\n\n")
                f.write("---\n\n")
                f.write(conversation['processed_text'])
                
        except Exception as e:
            print(f"Error saving markdown: {e}")
            
    def monitor_claude(self):
        """Main monitoring loop"""
        print("Starting Claude monitoring...")
        
        while self.monitoring:
            try:
                # Find Claude app if not found
                if not self.claude_app:
                    self.claude_app = self.find_claude_app()
                    if not self.claude_app:
                        print("Waiting for Claude app...")
                        time.sleep(5)
                        continue
                        
                # # Check if Claude app is still running
                # if not self.claude_app.isActive():
                #     print("Claude app not active")
                #     self.claude_app = None
                #     time.sleep(self.check_interval)
                #     continue
                    
                # Extract conversation content
                raw_content = self.get_claude_window_content()
                conversation = self.process_conversation_content(raw_content)
                
                if conversation:
                    # Check if conversation has changed
                    current_hash = self.generate_conversation_hash(conversation)
                    
                    if current_hash != self.last_conversation_hash:
                        print("New conversation content detected")
                        
                        if self.auto_save_enabled:
                            self.save_conversation(conversation)
                            
                        self.last_conversation_hash = current_hash
                    else:
                        print("No changes detected")
                        
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(self.check_interval)
                
    def start_monitoring(self):
        """Start the monitoring process"""
        if not self.check_accessibility_permissions():
            return False
            
        self.monitoring = True
        
        # Start monitoring in a separate thread
        monitor_thread = threading.Thread(target=self.monitor_claude, daemon=True)
        monitor_thread.start()
        
        return True
        
    def stop_monitoring(self):
        """Stop the monitoring process"""
        print("Stopping monitoring...")
        self.monitoring = False
        
    def manual_save(self):
        """Manually trigger a save"""
        print("Manual save triggered...")
        raw_content = self.get_claude_window_content()
        conversation = self.process_conversation_content(raw_content)
        
        if conversation:
            self.save_conversation(conversation)
            return True
        else:
            print("No conversation content found")
            return False


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print("\nShutting down...")
    archiver.stop_monitoring()
    sys.exit(0)


def main():
    global archiver
    
    print("Claude Desktop Archiver Starting...")
    print("Press Ctrl+C to stop")
    
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create archiver instance
    archiver = ClaudeArchiver()
    
    # Start monitoring
    if archiver.start_monitoring():
        print("Monitoring started successfully")
        
        # Keep the main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    else:
        print("Failed to start monitoring")


if __name__ == "__main__":
    main()