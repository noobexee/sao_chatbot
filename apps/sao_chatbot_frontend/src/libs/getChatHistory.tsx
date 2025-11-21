export default async function getChatHistory(user_id: string, session_id: string) {
  const url = `http://localhost:8000/api/v1/history/${user_id}/${session_id}`;
  
  console.log(`Fetching history from: ${url}`);

  const response = await fetch(url, {
    cache: "no-store",
  });

  if (!response.ok) {
   
    return { success: true, data: { messages: [] } };
  }

  return await response.json();
}