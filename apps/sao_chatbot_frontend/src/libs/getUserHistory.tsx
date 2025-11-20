export default async function getUserHistory(user_id : string) {
    console.log(`http://localhost:8000/api/v1/sessions/${user_id}`)
    const response = await fetch(`http://localhost:8000/api/v1/sessions/${user_id}`) 
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