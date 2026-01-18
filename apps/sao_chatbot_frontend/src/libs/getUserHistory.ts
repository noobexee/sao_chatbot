import { getBaseUrl } from "./config"

export default async function getUserHistory(user_id : string) {
    const baseUrl = getBaseUrl()
    const response = await fetch(`${baseUrl}/api/v1/chatbot/sessions/${user_id}`) 
    if(!response.ok) {
        throw new Error("Failed to fetch history")
    }
    return await response.json()
}


//{
//    "success": true,
//    "message": "Sessions retrieved successfully",
//    "data": [
//        {
//            "session_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
//            "title": "What is a neural network?",
//            "created_at": "2025-11-19T16:29:44.256365+00:00"
//        }
//   ]
//}