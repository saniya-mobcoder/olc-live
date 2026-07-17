"use client";

import { MapContainer, Marker, Popup, TileLayer, CircleMarker } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { MatchResult, Requirement } from "@/lib/types";

const icon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
});

export function TalentMap({
  requirement,
  shortlist,
}: {
  requirement: Requirement;
  shortlist: MatchResult[];
}) {
  const center: [number, number] = [requirement.latitude, requirement.longitude];

  return (
    <div className="h-72 w-full overflow-hidden border border-[var(--olc-ink)]/10">
      <MapContainer center={center} zoom={7} scrollWheelZoom={false} style={{ height: "100%", width: "100%" }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Marker position={center} icon={icon}>
          <Popup>
            Production: {requirement.city}, {requirement.country}
          </Popup>
        </Marker>
        {shortlist.map((row) =>
          row.talent ? (
            <CircleMarker
              key={row.talent_id}
              center={[row.talent.latitude, row.talent.longitude]}
              radius={8}
              pathOptions={{ color: "#0b3d2e", fillColor: "#c45c3e", fillOpacity: 0.85 }}
            >
              <Popup>
                #{row.rank} {row.talent.full_name} — {row.distance_km} km
              </Popup>
            </CircleMarker>
          ) : null
        )}
      </MapContainer>
    </div>
  );
}
