export function todayLocalISODate(): string {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

export function formatEntryDate(isoDate: string, locale?: string): string {
  return new Date(`${isoDate}T00:00:00`).toLocaleDateString(locale);
}

const RELATIVE_TIME_UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ['year', 60 * 60 * 24 * 365],
  ['month', 60 * 60 * 24 * 30],
  ['week', 60 * 60 * 24 * 7],
  ['day', 60 * 60 * 24],
  ['hour', 60 * 60],
  ['minute', 60],
];

export function formatRelativeTime(isoDateTime: string, locale?: string): string {
  const diffSeconds = (new Date(isoDateTime).getTime() - Date.now()) / 1000;
  const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' });
  for (const [unit, secondsInUnit] of RELATIVE_TIME_UNITS) {
    if (Math.abs(diffSeconds) >= secondsInUnit) {
      return rtf.format(Math.round(diffSeconds / secondsInUnit), unit);
    }
  }
  return rtf.format(Math.round(diffSeconds), 'second');
}
