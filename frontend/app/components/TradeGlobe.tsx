"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";
import type { GlobeMethods } from "react-globe.gl";
import { MeshPhongMaterial } from "three";
import type { CountryIntel } from "../data/countries";

const Globe = dynamic(() => import("react-globe.gl"), {
  ssr: false,
});

type TradeGlobeProps = {
  countries: CountryIntel[];
  selectedCountry: CountryIntel | null;
  onSelect: (country: CountryIntel) => void;
};

type CountryFeature = {
  type: "Feature";
  properties: {
    ADMIN: string;
    ISO_A2: string;
  };
  geometry: {
    type: "Polygon" | "MultiPolygon";
    coordinates: unknown[];
  };
};

type CountryGeoJson = {
  type: "FeatureCollection";
  features: CountryFeature[];
};

const chinaOrigin = {
  startLat: 31.2,
  startLng: 121.4,
};

function countryFromObject(value: object) {
  return value as CountryIntel;
}

export function TradeGlobe({
  countries,
  selectedCountry,
  onSelect,
}: TradeGlobeProps) {
  const globeRef = useRef<GlobeMethods | undefined>(undefined);
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 760, height: 680 });
  const [ready, setReady] = useState(false);
  const [landFeatures, setLandFeatures] = useState<CountryFeature[]>([]);

  const globeMaterial = useMemo(
    () =>
      new MeshPhongMaterial({
        color: "#f0f2ee",
        emissive: "#f8f9f6",
        emissiveIntensity: 0.12,
        shininess: 2,
        transparent: true,
        opacity: 0.9,
      }),
    [],
  );

  const targetByCode = useMemo(
    () => new Map(countries.map((country) => [country.code, country])),
    [countries],
  );

  const targetFeatures = useMemo(
    () =>
      landFeatures.filter((feature) =>
        targetByCode.has(feature.properties.ISO_A2),
      ),
    [landFeatures, targetByCode],
  );

  const arcs = useMemo(
    () =>
      selectedCountry
        ? [
            {
              ...chinaOrigin,
              endLat: selectedCountry.lat,
              endLng: selectedCountry.lng,
              country: selectedCountry.name,
            },
          ]
        : [],
    [selectedCountry],
  );

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;

    const updateSize = () => {
      const bounds = element.getBoundingClientRect();
      setSize({
        width: Math.max(320, Math.round(bounds.width)),
        height: Math.max(420, Math.round(bounds.height)),
      });
    };

    updateSize();
    const observer = new ResizeObserver(updateSize);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    let active = true;

    fetch("/countries-110m.geojson")
      .then((response) => response.json() as Promise<CountryGeoJson>)
      .then((data) => {
        if (active) setLandFeatures(data.features);
      })
      .catch(() => {
        if (active) setLandFeatures([]);
      });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!ready || !globeRef.current) return;

    const controls = globeRef.current.controls();
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.autoRotate = !selectedCountry;
    controls.autoRotateSpeed = 0.34;

    if (selectedCountry) {
      globeRef.current.pointOfView(
        {
          lat: selectedCountry.lat,
          lng: selectedCountry.lng,
          altitude: 0.78,
        },
        1050,
      );
    } else {
      globeRef.current.pointOfView(
        { lat: 20, lng: 82, altitude: 1.92 },
        900,
      );
    }
  }, [ready, selectedCountry]);

  return (
    <div className="globe-stage" ref={containerRef} aria-label="重点国家交互地球">
      <div className={`globe-canvas ${ready ? "is-ready" : ""}`}>
        <Globe
          ref={globeRef}
          width={size.width}
          height={size.height}
          backgroundColor="rgba(0,0,0,0)"
          globeMaterial={globeMaterial}
          showGraticules
          showAtmosphere
          atmosphereColor="#a8bbb4"
          atmosphereAltitude={0.1}
          globeOffset={selectedCountry ? [-112, 10] : [-24, 12]}
          hexPolygonsData={landFeatures}
          hexPolygonGeoJsonGeometry="geometry"
          hexPolygonUseDots
          hexPolygonResolution={3}
          hexPolygonDotResolution={12}
          hexPolygonMargin={0.46}
          hexPolygonColor={(feature) => {
            const code = (feature as CountryFeature).properties.ISO_A2;
            if (code === selectedCountry?.code) return "#c98a1b";
            if (targetByCode.has(code)) return "rgba(11,143,120,.86)";
            return "rgba(43,57,52,.46)";
          }}
          hexPolygonAltitude={(feature) => {
            const code = (feature as CountryFeature).properties.ISO_A2;
            if (code === selectedCountry?.code) return 0.024;
            if (targetByCode.has(code)) return 0.012;
            return 0.006;
          }}
          hexPolygonLabel={(feature) => {
            const code = (feature as CountryFeature).properties.ISO_A2;
            const country = targetByCode.get(code);
            return country
              ? `<div class="globe-tooltip"><strong>${country.name}</strong><span>${country.updateCount} 条动态 · 完整度 ${country.completeness}%</span></div>`
              : "";
          }}
          onHexPolygonClick={(feature) => {
            const code = (feature as CountryFeature).properties.ISO_A2;
            const country = targetByCode.get(code);
            if (country) onSelect(country);
          }}
          hexPolygonsTransitionDuration={760}
          polygonsData={targetFeatures}
          polygonGeoJsonGeometry="geometry"
          polygonAltitude={0.004}
          polygonCapColor={(feature) =>
            (feature as CountryFeature).properties.ISO_A2 ===
            selectedCountry?.code
              ? "rgba(201,138,27,.07)"
              : "rgba(11,143,120,.018)"
          }
          polygonSideColor={() => "rgba(255,255,255,0)"}
          polygonStrokeColor={(feature) =>
            (feature as CountryFeature).properties.ISO_A2 ===
            selectedCountry?.code
              ? "rgba(201,138,27,.72)"
              : "rgba(11,143,120,.12)"
          }
          polygonLabel={(feature) => {
            const code = (feature as CountryFeature).properties.ISO_A2;
            const country = targetByCode.get(code);
            return country
              ? `<div class="globe-tooltip"><strong>${country.name}</strong><span>点击查看政策情报</span></div>`
              : "";
          }}
          onPolygonClick={(feature) => {
            const code = (feature as CountryFeature).properties.ISO_A2;
            const country = targetByCode.get(code);
            if (country) onSelect(country);
          }}
          polygonsTransitionDuration={760}
          pointsData={countries}
          pointLat="lat"
          pointLng="lng"
          pointColor={(point) =>
            countryFromObject(point).id === selectedCountry?.id
              ? "#c98a1b"
              : "#0b8f78"
          }
          pointAltitude={(point) =>
            countryFromObject(point).id === selectedCountry?.id ? 0.16 : 0.08
          }
          pointRadius={(point) =>
            countryFromObject(point).id === selectedCountry?.id ? 0.42 : 0.25
          }
          pointLabel={(point) => {
            const country = countryFromObject(point);
            return `<div class="globe-tooltip"><strong>${country.name}</strong><span>${country.updateCount} 条动态 · 完整度 ${country.completeness}%</span></div>`;
          }}
          pointsTransitionDuration={760}
          onPointClick={(point) => onSelect(countryFromObject(point))}
          ringsData={selectedCountry ? [selectedCountry] : []}
          ringLat="lat"
          ringLng="lng"
          ringColor={() => ["rgba(201,138,27,.9)", "rgba(201,138,27,0)"]}
          ringMaxRadius={3.7}
          ringPropagationSpeed={2.1}
          ringRepeatPeriod={980}
          arcsData={arcs}
          arcStartLat="startLat"
          arcStartLng="startLng"
          arcEndLat="endLat"
          arcEndLng="endLng"
          arcColor={() => ["rgba(11,143,120,.2)", "rgba(201,138,27,.86)"]}
          arcStroke={0.42}
          arcAltitudeAutoScale={0.36}
          arcDashLength={0.28}
          arcDashGap={0.14}
          arcDashAnimateTime={1250}
          arcsTransitionDuration={900}
          onGlobeReady={() => setReady(true)}
          rendererConfig={{
            antialias: true,
            alpha: true,
            powerPreference: "high-performance",
          }}
        />
      </div>

      {!ready && (
        <div className="globe-loader">
          <span />
          <p>正在建立全球政策视图</p>
        </div>
      )}

      <div className="globe-vignette" />
      <div className="globe-origin">
        <span className="origin-dot" />
        上海出口中心
      </div>
    </div>
  );
}
