export function buildLocationQuery(location = {}) {
  if (!location) return "";

  const latitude = Number(location.latitude);
  const longitude = Number(location.longitude);
  if (Number.isFinite(latitude) && Number.isFinite(longitude)) {
    return `${latitude},${longitude}`;
  }

  const parts = [location.location_name, location.campus_name, location.address].filter(Boolean);
  return parts.join(", ").trim();
}

export function googleMapsSearchUrl(location) {
  const query = buildLocationQuery(location);
  if (!query) return "";
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(query)}`;
}

export function googleMapsEmbedUrl(location) {
  const query = buildLocationQuery(location);
  if (!query) return "";
  return `https://maps.google.com/maps?q=${encodeURIComponent(query)}&z=16&output=embed`;
}
