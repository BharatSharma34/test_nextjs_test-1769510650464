import axios from "axios";
import getConfig from "next/config";

const { publicRuntimeConfig } = getConfig();
const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL
  || `${publicRuntimeConfig.basePath}/api`;

export const api = axios.create({
  baseURL: apiBaseUrl,
  timeout: 300000 // 5 minutes default timeout for LLM operations
});