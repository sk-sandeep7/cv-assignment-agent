// Production API base URL - update this with your actual Render URL
const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? 'http://cv-assignment-agent-production.up.railway.app' 
  : 'http://localhost:8000';

export default API_BASE_URL;
