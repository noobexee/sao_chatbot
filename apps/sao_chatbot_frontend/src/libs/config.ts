export const getBaseUrl = () => {

  if (typeof window !== 'undefined') {
    return ''; 
  }
  
  return process.env.INTERNAL_API_URL || 'http://backend:8000';
};