import axios, { isAxiosError } from 'axios';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '',
  withCredentials: true,
});

export const getApiErrorMessage = (error: unknown): string => {
  const data = isAxiosError(error) ? error.response?.data : undefined;

  if (data && typeof data === 'object') {
    if (
      'error' in data &&
      data.error &&
      typeof data.error === 'object' &&
      'message' in data.error
    ) {
      return String((data.error as { message: unknown }).message);
    }
    if ('detail' in data && typeof data.detail === 'string') {
      return data.detail;
    }
  }

  return '요청 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
};
