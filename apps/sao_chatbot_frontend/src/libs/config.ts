export const getBaseUrl = () => {
  if (typeof window !== 'undefined') {
    return process.env.NEXT_PUBLIC_RAG_API_URL;
  }
  
  return process.env.INTERNAL_API_URL || 'http://backend:8000';
};