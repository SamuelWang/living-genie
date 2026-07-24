export function todayLocalISODate(): string {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

export function formatEntryDate(isoDate: string, locale?: string): string {
  return new Date(`${isoDate}T00:00:00`).toLocaleDateString(locale);
}
