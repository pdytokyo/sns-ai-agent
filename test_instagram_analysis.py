import sys
import json
from instagram_analyzer import process_instagram_post, get_instagram_analysis

sample_posts = [
    "https://www.instagram.com/p/C5NJJfJSQnP/",  # Example high engagement post
    "https://www.instagram.com/p/C5Ij-ufSdnm/",  # Example post
    "https://www.instagram.com/p/C5Hg2YJSQ-K/"   # Example post
]

def test_instagram_analysis():
    """Test Instagram analysis functionality with sample posts"""
    results = []
    
    print("=== Instagram Analysis Testing ===")
    
    for i, post_url in enumerate(sample_posts):
        print(f"\nProcessing post {i+1}: {post_url}")
        
        client_id = 1 if i == 0 else None
        
        try:
            result = process_instagram_post(post_url, client_id, use_mock=True)
            
            if result.get("success", False):
                print(f"✅ Successfully processed post")
                print(f"Views: {result.get('views', 'N/A')}")
                print(f"Likes: {result.get('likes', 'N/A')}")
                print(f"Comments: {result.get('comments', 'N/A')}")
                print(f"Engagement rate: {result.get('engagement_rate', 0):.2f}%")
                print(f"High engagement: {result.get('high_engagement', False)}")
                
                if result.get("transcript"):
                    print(f"✅ Transcript generated ({len(result['transcript'])} characters)")
                    transcript_preview = result["transcript"][:100] + "..." if len(result["transcript"]) > 100 else result["transcript"]
                    print(f"Transcript preview: {transcript_preview}")
                
                if result.get("rewritten_script"):
                    print(f"✅ Script rewritten ({len(result['rewritten_script'])} characters)")
                    rewrite_preview = result["rewritten_script"][:100] + "..." if len(result["rewritten_script"]) > 100 else result["rewritten_script"]
                    print(f"Rewrite preview: {rewrite_preview}")
                
                results.append({
                    "post_url": post_url,
                    "success": True,
                    "views": result.get("views", 0),
                    "likes": result.get("likes", 0),
                    "comments": result.get("comments", 0),
                    "engagement_rate": result.get("engagement_rate", 0),
                    "high_engagement": result.get("high_engagement", False),
                    "has_transcript": bool(result.get("transcript")),
                    "has_rewrite": bool(result.get("rewritten_script"))
                })
            else:
                print(f"❌ Failed to process post: {result.get('error', 'Unknown error')}")
                results.append({
                    "post_url": post_url,
                    "success": False,
                    "error": result.get("error", "Unknown error")
                })
        except Exception as e:
            print(f"❌ Exception during processing: {str(e)}")
            results.append({
                "post_url": post_url,
                "success": False,
                "error": str(e)
            })
    
    print("\n=== Test Summary ===")
    successful = sum(1 for r in results if r.get("success", False))
    print(f"Total posts processed: {len(results)}")
    print(f"Successfully processed: {successful}")
    print(f"Failed: {len(results) - successful}")
    
    high_engagement = sum(1 for r in results if r.get("high_engagement", False))
    print(f"High engagement posts: {high_engagement}")
    
    transcribed = sum(1 for r in results if r.get("has_transcript", False))
    print(f"Posts with transcripts: {transcribed}")
    
    rewritten = sum(1 for r in results if r.get("has_rewrite", False))
    print(f"Posts with rewrites: {rewritten}")
    
    print("\n=== Database Verification ===")
    db_entries = get_instagram_analysis()
    print(f"Total entries in database: {len(db_entries)}")
    
    if db_entries:
        print("\n=== Database Entry Details ===")
        for i, entry in enumerate(db_entries[:3]):  # 最大3件表示
            print(f"\nEntry {i+1}:")
            print(f"Post URL: {entry.get('post_url', 'N/A')}")
            print(f"Views: {entry.get('views', 'N/A')}")
            print(f"Likes: {entry.get('likes', 'N/A')}")
            print(f"Comments: {entry.get('comments', 'N/A')}")
            print(f"High Engagement: {bool(entry.get('high_engagement', False))}")
            
            if entry.get('transcript'):
                print(f"Has Transcript: Yes ({len(entry['transcript'])} chars)")
            else:
                print("Has Transcript: No")
                
            if entry.get('rewritten_script'):
                print(f"Has Rewritten Script: Yes ({len(entry['rewritten_script'])} chars)")
            else:
                print("Has Rewritten Script: No")
    
    return results

if __name__ == "__main__":
    results = test_instagram_analysis()
    
    with open("instagram_analysis_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\nResults saved to instagram_analysis_results.json")
