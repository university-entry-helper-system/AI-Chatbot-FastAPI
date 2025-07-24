import asyncio
import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_URL = "http://localhost:8001/api/v1"

async def test_knowledge_service():
    """Test knowledge service trực tiếp"""
    print("🧪 Testing Knowledge Service...")
    
    try:
        from app.services.knowledge_service import knowledge_service
        
        # Test 1: Search by intent
        print("\n1️⃣ Testing search by intent:")
        score_data = knowledge_service.search_by_intent("score_lookup")
        print(f"✅ Score lookup data: {score_data.get('description', 'N/A')}")
        
        # Test 2: Search by keywords
        print("\n2️⃣ Testing keyword search:")
        results = knowledge_service.search_by_keywords("tôi muốn tra cứu điểm thi")
        print(f"✅ Found {len(results)} relevant categories")
        for result in results[:2]:
            print(f"   - {result['category']}: relevance {result['relevance_score']}")
        
        # Test 3: Comprehensive search
        print("\n3️⃣ Testing comprehensive search:")
        context = knowledge_service.search_comprehensive(
            "Tôi muốn tư vấn chọn trường công nghệ thông tin",
            "school_recommendation"
        )
        print(f"✅ Context generated with {len(context)} sections")
        if context.get('relevant_info', {}).get('major'):
            major_info = context['relevant_info']['major']
            print(f"   - Found major: {major_info.get('name', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Knowledge service test failed: {e}")
        return False

async def test_enhanced_chat():
    """Test enhanced chat với knowledge base"""
    print("\n🤖 Testing Enhanced Chat with Knowledge Base...")
    
    # Create session
    session_response = requests.post(f"{BASE_URL}/chat/session/test_kb_user")
    if session_response.status_code != 200:
        print(f"❌ Failed to create session: {session_response.text}")
        return False
    
    session_id = session_response.json()["data"]["session_id"]
    print(f"✅ Session created: {session_id}")
    
    # Test cases với knowledge base
    test_cases = [
        {
            "message": "Chào bạn, tôi muốn tư vấn ngành công nghệ thông tin",
            "expected_features": ["major_info", "job_opportunities", "salary_range"],
            "description": "Major advice với knowledge base"
        },
        {
            "message": "Trường Bách Khoa Hà Nội có những ngành nào mạnh?",
            "expected_features": ["school_info", "strong_majors", "tuition_fee"],
            "description": "School recommendation với knowledge base"
        },
        {
            "message": "Tôi có 25 điểm khối A00, nên chọn trường nào?",
            "expected_features": ["score_analysis", "suitable_schools", "recommendations"],
            "description": "Score-based recommendation"
        },
        {
            "message": "Lịch đăng ký xét tuyển 2024 như thế nào?",
            "expected_features": ["timeline", "deadlines", "registration"],
            "description": "Schedule information"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i}: {test_case['description']} ---")
        print(f"Input: {test_case['message']}")
        
        # Send message
        message_payload = {
            "session_id": session_id,
            "user_message": test_case["message"]
        }
        
        response = requests.post(
            f"{BASE_URL}/chat/message",
            headers={"Content-Type": "application/json"},
            json=message_payload
        )
        
        if response.status_code != 200:
            print(f"❌ Failed: {response.text}")
            continue
        
        result = response.json()["data"]
        bot_response = result["bot_response"]
        
        print(f"Intent: {result.get('intent', 'N/A')}")
        print(f"Entities: {result.get('entities', {})}")
        print(f"Response length: {len(bot_response)} chars")
        print(f"Response preview: {bot_response[:150]}...")
        
        # Check for expected features
        features_found = []
        response_lower = bot_response.lower()
        
        for feature in test_case["expected_features"]:
            if any(keyword in response_lower for keyword in [
                feature.replace("_", " "), feature.replace("_", ""), feature
            ]):
                features_found.append(feature)
        
        if features_found:
            print(f"✅ Found features: {', '.join(features_found)}")
        else:
            print("⚠️ Expected features not clearly found in response")
        
        # Check if response seems enhanced (not fallback)
        fallback_indicators = ["sự cố kỹ thuật", "thử lại", "đang gặp vấn đề"]
        is_fallback = any(indicator in response_lower for indicator in fallback_indicators)
        
        if not is_fallback:
            print("✅ Enhanced response (not fallback)")
        else:
            print("❌ Fallback response detected")

def test_knowledge_base_file():
    """Kiểm tra knowledge base file"""
    print("📁 Testing Knowledge Base File...")
    
    import json
    from pathlib import Path
    
    try:
        kb_path = Path("app/data/knowledge_base.json")
        
        if not kb_path.exists():
            print(f"❌ Knowledge base file not found: {kb_path}")
            print("💡 Run: python setup_knowledge_base.py")
            return False
        
        with open(kb_path, 'r', encoding='utf-8') as f:
            kb_data = json.load(f)
        
        print(f"✅ Knowledge base loaded successfully")
        print(f"📊 Categories: {len(kb_data)}")
        
        # Check each category
        for category, data in kb_data.items():
            keywords_count = len(data.get('keywords', []))
            print(f"   - {category}: {keywords_count} keywords")
        
        return True
        
    except Exception as e:
        print(f"❌ Knowledge base file test failed: {e}")
        return False

def test_environment():
    """Check environment setup"""
    print("🔧 Checking Environment...")
    
    # Check OpenAI key
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key or openai_key == "sk-your-openai-api-key-here":
        print("❌ OPENAI_API_KEY not configured")
        return False
    else:
        print("✅ OPENAI_API_KEY configured")
    
    # Check server
    try:
        response = requests.get(f"{BASE_URL.replace('/api/v1', '')}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
        else:
            print(f"⚠️ Server responded with {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to server: {e}")
        print("💡 Start server: python -m uvicorn app.main:app --reload --port 8001")
        return False
    
    return True

async def main():
    """Main test function"""
    print("🧪 Knowledge Base Integration Test")
    print("=" * 50)
    
    all_tests_passed = True
    
    # Test 1: Environment
    print("\n🔧 STEP 1: Environment Check")
    if not test_environment():
        print("❌ Environment check failed")
        all_tests_passed = False
    
    # Test 2: Knowledge base file
    print("\n📁 STEP 2: Knowledge Base File")
    if not test_knowledge_base_file():
        print("❌ Knowledge base file check failed")
        all_tests_passed = False
    
    # Test 3: Knowledge service
    print("\n🧪 STEP 3: Knowledge Service")
    if not await test_knowledge_service():
        print("❌ Knowledge service test failed")
        all_tests_passed = False
    
    # Test 4: Enhanced chat
    print("\n🤖 STEP 4: Enhanced Chat")
    await test_enhanced_chat()
    
    # Summary
    print("\n" + "=" * 50)
    if all_tests_passed:
        print("✅ All tests completed successfully!")
        print("\n🎉 Your Knowledge Base Integration is working!")
        print("\n💡 Try these commands:")
        print("- 'Tôi muốn tư vấn ngành công nghệ thông tin'")
        print("- 'Trường Bách Khoa có những ngành gì?'")
        print("- 'Tôi có 24 điểm nên chọn trường nào?'")
    else:
        print("⚠️ Some tests failed. Please check the issues above.")
        print("\n🔧 Common fixes:")
        print("1. Run: python setup_knowledge_base.py")
        print("2. Create all required service files")
        print("3. Set OPENAI_API_KEY in .env")
        print("4. Start server: uvicorn app.main:app --reload")
    
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())