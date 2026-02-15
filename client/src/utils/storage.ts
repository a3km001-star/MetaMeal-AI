export const readBoolean = (key: string, fallback = false): boolean => {
  const raw = localStorage.getItem(key);
  if (raw === null) return fallback;
  try {
    return JSON.parse(raw) as boolean;
  } catch {
    return fallback;
  }
};

export const writeBoolean = (key: string, value: boolean): void => {
  localStorage.setItem(key, JSON.stringify(value));
};
