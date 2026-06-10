#!/usr/bin/env python3
"""
Script to fetch protobuf schemas from GitHub API and store in proto folder
Fetches byova_common.proto and voicevirtualagent.proto
"""

import requests
import base64
import os
import sys

def fetch_proto_file(api_url, filename, proto_folder):
    """
    Fetch a single proto file from GitHub API and decode base64 content
    """
    
    try:
        print(f"🔗 Fetching {filename}...")
        print(f"   URL: {api_url}")
        
        # Make API request
        response = requests.get(api_url)
        response.raise_for_status()
        
        # Parse JSON response
        data = response.json()
        
        if "content" not in data:
            raise Exception(f"No 'content' field found in API response for {filename}")
        
        # Base64 decode the content
        encoded_content = data["content"]
        decoded_content = base64.b64decode(encoded_content).decode('utf-8')
        
        print(f"✅ Successfully fetched and decoded {filename} ({len(decoded_content)} characters)")
        
        # Write decoded content to proto file
        proto_file_path = os.path.join(proto_folder, filename)
        
        with open(proto_file_path, 'w', encoding='utf-8') as f:
            f.write(decoded_content)
        
        print(f"💾 Proto schema saved to: {proto_file_path}")
        print(f"📄 File size: {os.path.getsize(proto_file_path)} bytes")
        
        # Show first few lines for verification
        lines = decoded_content.split('\n')[:3]
        print(f"📋 First few lines of {filename}:")
        for i, line in enumerate(lines, 1):
            print(f"   {i}: {line}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ HTTP Error for {filename}: {e}")
        return False
    except Exception as e:
        print(f"❌ Error for {filename}: {e}")
        return False

def fetch_and_decode_proto_schemas():
    """
    Fetch proto files from GitHub API. Falls back to bundled copies in src/proto/
    if the network request fails.
    """
    
    proto_files = [
        {
            "url": "https://api.github.com/repos/webex/dataSourceSchemas/git/blobs/a22cf246a1e0a3302c48100aea8e2c5c09b66f0a",
            "filename": "byova_common.proto"
        },
        {
            "url": "https://api.github.com/repos/webex/dataSourceSchemas/git/blobs/2cdba566b9b45d029874ecf4f649630741777023", 
            "filename": "voicevirtualagent.proto"
        },
        {
            "url": "https://api.github.com/repos/webex/dataSourceSchemas/git/blobs/0d56517d9a6bbe231000f19aafcbe755679efeb6",
            "filename": "conversationaudioforking.proto"
        },
        {
            "url": "https://api.github.com/repos/webex/dataSourceSchemas/git/blobs/68f44b18b760bc3e9296f017e78118e64d112758",
            "filename": "media_service_common.proto"
        }
    ]
    
    proto_folder = "./src/proto"
    os.makedirs(proto_folder, exist_ok=True)
    print(f"📁 Proto folder: {os.path.abspath(proto_folder)}")
    
    success_count = 0
    fallback_count = 0

    for proto_file in proto_files:
        print(f"\n{'='*50}")
        if fetch_proto_file(proto_file["url"], proto_file["filename"], proto_folder):
            success_count += 1
        else:
            fallback_path = os.path.join(proto_folder, proto_file["filename"])
            if os.path.exists(fallback_path):
                print(f"⚠️  Fetch failed — using bundled file: {fallback_path}")
                fallback_count += 1
            else:
                print(f"❌ No bundled fallback found for {proto_file['filename']}")
        print(f"{'='*50}")

    total_available = success_count + fallback_count
    return total_available == len(proto_files)

def main():
    """Main function"""
    print("🚀 GitHub Proto Schema Fetcher")
    print("=" * 40)
    
    success = fetch_and_decode_proto_schemas()
    
    if success:
        print("\n✅ All proto schemas ready.")
        sys.exit(0)
    else:
        print("\n💥 Proto schema fetch failed and no bundled fallback available!")
        sys.exit(1)

if __name__ == "__main__":
    main()
