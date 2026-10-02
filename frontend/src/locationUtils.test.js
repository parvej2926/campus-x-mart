import test from "node:test";
import assert from "node:assert/strict";
import { buildLocationQuery, googleMapsEmbedUrl, googleMapsSearchUrl } from "./locationUtils.js";

test("buildLocationQuery prefers coordinates when available", () => {
  const query = buildLocationQuery({ latitude: 23.7806, longitude: 90.407, location_name: "Library" });
  assert.equal(query, "23.7806,90.407");
});

test("buildLocationQuery falls back to location text when coordinates are missing", () => {
  const query = buildLocationQuery({ location_name: "Library entrance", campus_name: "Dhaka University", address: "Academic building" });
  assert.equal(query, "Library entrance, Dhaka University, Academic building");
});

test("Google Maps URLs are generated for valid locations", () => {
  const location = { latitude: 23.7806, longitude: 90.407, location_name: "Library" };
  assert.equal(googleMapsSearchUrl(location), "https://www.google.com/maps/search/?api=1&query=23.7806%2C90.407");
  assert.equal(googleMapsEmbedUrl(location), "https://maps.google.com/maps?q=23.7806%2C90.407&z=16&output=embed");
});

test("location helpers return blank values for empty data", () => {
  assert.equal(buildLocationQuery({}), "");
  assert.equal(googleMapsSearchUrl({}), "");
  assert.equal(googleMapsEmbedUrl({}), "");
});
