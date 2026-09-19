export const CONTINENTS = [
  "Africa",
  "Asia",
  "Australia/Oceania",
  "Europe",
  "North America",
  "South America",
] as const;

export const CONTINENT_COLORS: Record<string, [number, number, number]> = {
  Africa: [16, 185, 129],
  Asia: [14, 165, 233],
  "Australia/Oceania": [139, 92, 246],
  Europe: [100, 116, 139],
  "North America": [245, 158, 11],
  "South America": [249, 115, 22],
};

export function continentColor(continent: string): string {
  const rgb = CONTINENT_COLORS[continent] ?? [148, 163, 184];
  return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
}
