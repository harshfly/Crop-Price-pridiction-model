const BASE_URL = 'http://localhost:8000';

// Default API Key (Anonymous/Free tier logic on backend)
let currentApiKey = '';

export const setApiKey = (key) => {
  currentApiKey = key;
};

const getHeaders = () => {
  const headers = {
    'Content-Type': 'application/json',
  };
  if (currentApiKey) {
    headers['X-API-Key'] = currentApiKey;
  }
  return headers;
};

export const predictPrice = async (crop, mandi, daysAhead = 7) => {
  try {
    const response = await fetch(`${BASE_URL}/predict/price`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({
        crop,
        mandi,
        days_ahead: daysAhead
      })
    });
    
    if (!response.ok) {
      if (response.status === 429) throw new Error('Rate limit exceeded. Please upgrade your plan.');
      if (response.status === 401) throw new Error('Invalid API Key.');
      throw new Error('API Request Failed');
    }
    
    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
};

export const getCrops = async () => {
  try {
    const response = await fetch(`${BASE_URL}/crops`, { headers: getHeaders() });
    if (!response.ok) return ['Wheat', 'Onion', 'Tomato', 'Potato']; // Fallback
    const data = await response.json();
    return data.crops || ['Wheat', 'Onion', 'Tomato', 'Potato'];
  } catch (e) {
    return ['Wheat', 'Onion', 'Tomato', 'Potato'];
  }
};

export const getMandis = async () => {
  try {
    const response = await fetch(`${BASE_URL}/mandis`, { headers: getHeaders() });
    if (!response.ok) return ['Indore', 'Bhopal', 'Nashik', 'Pune']; // Fallback
    const data = await response.json();
    return data.mandis || ['Indore', 'Bhopal', 'Nashik', 'Pune'];
  } catch (e) {
    return ['Indore', 'Bhopal', 'Nashik', 'Pune'];
  }
};

export const getFuelPrices = async () => {
  try {
    const response = await fetch(`${BASE_URL}/fuel/prices`, { headers: getHeaders() });
    if (!response.ok) throw new Error('Failed to fetch fuel prices');
    return await response.json();
  } catch (e) {
    return { prices: [] };
  }
};

export const getWeatherImpact = async (city, crop) => {
  try {
    const response = await fetch(`${BASE_URL}/weather/impact?city=${encodeURIComponent(city)}&crop=${encodeURIComponent(crop)}`, { headers: getHeaders() });
    if (!response.ok) throw new Error('Failed to fetch weather');
    return await response.json();
  } catch (e) {
    return null;
  }
};

export const getBestMandi = async (crop, quantity, lat, lon) => {
  try {
    const response = await fetch(`${BASE_URL}/mandis/compare?crop=${encodeURIComponent(crop)}&quantity=${quantity}&from_lat=${lat}&from_lon=${lon}`, { headers: getHeaders() });
    if (!response.ok) throw new Error('Failed to fetch best mandi');
    return await response.json();
  } catch (e) {
    return null;
  }
};
