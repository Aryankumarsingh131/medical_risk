import React, { useEffect, useLayoutEffect, useRef, useState } from "react";
import { animate, motion } from "framer-motion";
import { ArrowUp, CircleCheck } from "lucide-react";

const STAGE_W = 1200;
const STAGE_H = 490;
const CENTER = { x: 600, y: 620 };
const RADIUS = { outer: 492, inner: 404 };

function positionOnRing(ring, angle) {
  const rad = (angle * Math.PI) / 180;
  const r = RADIUS[ring];
  return {
    left: CENTER.x + r * Math.cos(rad),
    top: CENTER.y - r * Math.sin(rad),
  };
}

function arcPath(r) {
  const dy = CENTER.y - STAGE_H;
  const dx = Math.sqrt(r * r - dy * dy);
  return `M ${CENTER.x - dx} ${STAGE_H} A ${r} ${r} 0 0 1 ${CENTER.x + dx} ${STAGE_H}`;
}

function OrbitAvatar({ src, alt, color, size = 68 }) {
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: "9999px",
        border: "2px solid rgba(255,255,255,0.2)",
        backgroundColor: "#161616",
        padding: "3px",
        boxShadow: "0 6px 20px rgba(0,0,0,0.3)",
      }}
    >
      <div
        style={{
          height: "100%",
          width: "100%",
          overflow: "hidden",
          borderRadius: "9999px",
          backgroundColor: color || "#2D6A5D",
        }}
      >
        <img
          src={src}
          alt={alt || "Avatar"}
          draggable={false}
          style={{
            height: "100%",
            width: "100%",
            userSelect: "none",
            objectFit: "cover",
            objectPosition: "top",
          }}
        />
      </div>
    </div>
  );
}

function OrbitPill({ icon, label }) {
  return (
    <div
      style={{
        display: "flex",
        minHeight: "32px",
        alignItems: "center",
        gap: "8px",
        whiteSpace: "nowrap",
        borderRadius: "9999px",
        border: "1px solid rgba(255,255,255,0.15)",
        backgroundColor: "rgba(22, 27, 34, 0.95)",
        backdropFilter: "blur(8px)",
        padding: "5px 12px",
        fontSize: "12.5px",
        fontWeight: 600,
        color: "#E6EDF3",
        boxShadow: "0 4px 14px rgba(0,0,0,0.25)",
      }}
    >
      <span style={{ display: "flex", alignItems: "center", fontSize: "14px" }}>{icon}</span>
      <span>{label}</span>
    </div>
  );
}

function OrbitCard({ emoji, badge }) {
  return (
    <div
      style={{
        position: "relative",
        display: "flex",
        height: "54px",
        width: "54px",
        alignItems: "center",
        justifyContent: "center",
        borderRadius: "14px",
        border: "1px solid rgba(255,255,255,0.15)",
        backgroundColor: "#1C2128",
        fontSize: "24px",
        boxShadow: "0 6px 18px rgba(0,0,0,0.3)",
      }}
    >
      <span style={{ userSelect: "none" }}>{emoji}</span>
      {badge !== undefined && (
        <span
          style={{
            position: "absolute",
            bottom: "-6px",
            right: "-8px",
            display: "flex",
            height: "18px",
            alignItems: "center",
            gap: "2px",
            borderRadius: "5px",
            border: "1px solid rgba(255,255,255,0.2)",
            backgroundColor: "#22272E",
            padding: "0 5px",
            fontSize: "10px",
            fontWeight: 700,
            color: "#57AB5A",
            boxShadow: "0 2px 6px rgba(0,0,0,0.2)",
          }}
        >
          <ArrowUp size={9} strokeWidth={2.4} />
          {badge}
        </span>
      )}
    </div>
  );
}

function OrbitStatus({ label }) {
  return (
    <div
      style={{
        display: "flex",
        height: "32px",
        alignItems: "center",
        gap: "6px",
        whiteSpace: "nowrap",
        borderRadius: "9999px",
        border: "1px solid #238636",
        backgroundColor: "rgba(35, 134, 54, 0.15)",
        backdropFilter: "blur(6px)",
        padding: "0 12px",
        fontSize: "13px",
        fontWeight: 600,
        color: "#3FB950",
        boxShadow: "0 4px 14px rgba(35, 134, 54, 0.2)",
      }}
    >
      <CircleCheck size={16} strokeWidth={2.4} color="#3FB950" />
      <span>{label}</span>
    </div>
  );
}

function OrbitCheck() {
  return (
    <div
      style={{
        display: "flex",
        height: "50px",
        width: "50px",
        alignItems: "center",
        justifyContent: "center",
        borderRadius: "9999px",
        border: "1px solid #238636",
        backgroundColor: "rgba(35, 134, 54, 0.2)",
        boxShadow: "0 6px 18px rgba(35, 134, 54, 0.25)",
      }}
    >
      <CircleCheck size={20} strokeWidth={2.5} color="#3FB950" />
    </div>
  );
}

function renderItem(item) {
  switch (item.kind) {
    case "avatar":
      return <OrbitAvatar {...item} />;
    case "pill":
      return <OrbitPill {...item} />;
    case "card":
      return <OrbitCard {...item} />;
    case "status":
      return <OrbitStatus {...item} />;
    case "check":
      return <OrbitCheck />;
    default:
      return null;
  }
}

function splitValue(value) {
  const m = value.match(/^([^\d]*)([\d.,]+)(.*)$/);
  if (!m) return null;
  const raw = m[2].replace(/,/g, "");
  const decimals = (raw.split(".")[1] ?? "").length;
  return { prefix: m[1], target: parseFloat(raw), decimals, suffix: m[3] };
}

function CountUp({ value, delay }) {
  const parts = splitValue(value);
  const [n, setN] = useState(0);

  useEffect(() => {
    if (!parts) return;
    const controls = animate(0, parts.target, {
      delay,
      duration: 1.6,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => setN(v),
    });
    return () => controls.stop();
  }, [value, delay]);

  if (!parts) return <>{value}</>;
  return (
    <>
      {parts.prefix}
      {n.toFixed(parts.decimals)}
      {parts.suffix}
    </>
  );
}

const reveal = {
  hidden: { opacity: 0, y: 14, filter: "blur(4px)" },
  show: { opacity: 1, y: 0, filter: "blur(0px)" },
};

export default function CommunityOrbit({
  items,
  stats,
  headline,
  tags = [],
  minScale = 0.55,
  className = "",
}) {
  const frameRef = useRef(null);
  const [scale, setScale] = useState(1);

  useLayoutEffect(() => {
    const frame = frameRef.current;
    if (!frame) return;
    const measure = () =>
      setScale(Math.min(1, Math.max(minScale, frame.clientWidth / STAGE_W)));
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(frame);
    return () => ro.disconnect();
  }, [minScale]);

  return (
    <section
      className={className}
      style={{
        width: "100%",
        paddingBottom: "3.5rem",
        color: "#FFFFFF",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div
        ref={frameRef}
        style={{
          position: "relative",
          margin: "0 auto",
          width: "100%",
          maxWidth: "1200px",
          overflow: "hidden",
          height: STAGE_H * scale,
        }}
      >
        <div
          style={{
            position: "absolute",
            left: "50%",
            top: 0,
            width: STAGE_W,
            height: STAGE_H,
            transform: `translateX(-50%) scale(${scale})`,
            transformOrigin: "top center",
          }}
        >
          <svg
            style={{
              pointerEvents: "none",
              position: "absolute",
              inset: 0,
              maskImage: "linear-gradient(to bottom, #000 62%, transparent 100%)",
              WebkitMaskImage: "linear-gradient(to bottom, #000 62%, transparent 100%)",
            }}
            width={STAGE_W}
            height={STAGE_H}
            viewBox={`0 0 ${STAGE_W} ${STAGE_H}`}
            fill="none"
          >
            <motion.path
              d={arcPath(RADIUS.outer)}
              stroke="rgba(255, 255, 255, 0.12)"
              strokeWidth={2}
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 1.4, ease: "easeOut" }}
            />
            <motion.path
              d={arcPath(RADIUS.inner)}
              stroke="rgba(45, 106, 93, 0.35)"
              strokeWidth={3}
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 1.4, ease: "easeOut", delay: 0.1 }}
            />
          </svg>

          {items.map((item, i) => (
            <motion.div
              key={i}
              style={{
                position: "absolute",
                transform: "translate(-50%, -50%)",
                ...positionOnRing(item.ring, item.angle),
              }}
              initial={{ opacity: 0, scale: 0.7 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, delay: 0.5 + i * 0.07, ease: [0.22, 1, 0.36, 1] }}
            >
              <motion.div
                animate={{ y: [0, -5, 0] }}
                transition={{
                  duration: 4 + (i % 4) * 0.6,
                  repeat: Infinity,
                  ease: "easeInOut",
                  delay: (i * 0.4) % 2,
                }}
                whileHover={{ scale: 1.08 }}
              >
                {renderItem(item)}
              </motion.div>
            </motion.div>
          ))}

          <div
            style={{
              position: "absolute",
              left: "50%",
              top: "390px",
              transform: "translateX(-50%)",
              display: "grid",
              gridAutoFlow: "column",
              gap: "3rem",
            }}
          >
            {stats.map((s, i) => (
              <motion.div
                key={s.label}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                }}
                variants={reveal}
                initial="hidden"
                animate="show"
                transition={{ duration: 0.6, delay: 0.9 + i * 0.12, ease: [0.22, 1, 0.36, 1] }}
              >
                <span
                  style={{
                    fontSize: "44px",
                    fontWeight: 700,
                    lineHeight: 1,
                    letterSpacing: "-0.02em",
                    color: "#FFFFFF",
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  <CountUp value={s.value} delay={0.9 + i * 0.12} />
                </span>
                <span
                  style={{
                    marginTop: "10px",
                    fontSize: "14px",
                    lineHeight: 1,
                    color: "rgba(255,255,255,0.6)",
                    fontWeight: 500,
                  }}
                >
                  {s.label}
                </span>
              </motion.div>
            ))}
          </div>
        </div>
      </div>

      <motion.h2
        style={{
          margin: "0.5rem auto 0",
          maxWidth: "680px",
          textAlign: "center",
          fontSize: "28px",
          fontWeight: 600,
          lineHeight: 1.25,
          letterSpacing: "-0.01em",
          color: "#FFFFFF",
        }}
        variants={reveal}
        initial="hidden"
        animate="show"
        transition={{ duration: 0.7, delay: 1.3, ease: [0.22, 1, 0.36, 1] }}
      >
        {headline}
      </motion.h2>

      {tags.length > 0 && (
        <div
          style={{
            margin: "28px auto 0",
            display: "flex",
            maxWidth: "800px",
            flexWrap: "wrap",
            justifyContent: "center",
            gap: "12px",
            padding: "0 1rem",
          }}
        >
          {tags.map((t, i) => {
            const Tag = t.href ? motion.a : motion.button;
            return (
              <Tag
                key={t.label}
                {...(t.href ? { href: t.href } : { type: "button" })}
                onClick={t.onClick}
                variants={reveal}
                initial="hidden"
                animate="show"
                transition={{ duration: 0.5, delay: 1.6 + i * 0.08, ease: [0.22, 1, 0.36, 1] }}
                whileHover={{ y: -2 }}
                whileTap={{ y: 0 }}
                style={{
                  display: "flex",
                  height: "40px",
                  alignItems: "center",
                  gap: "10px",
                  borderRadius: "9999px",
                  border: "1px solid rgba(255,255,255,0.15)",
                  backgroundColor: "#161B22",
                  paddingLeft: "6px",
                  paddingRight: "16px",
                  fontSize: "14px",
                  fontWeight: 500,
                  color: "#E6EDF3",
                  boxShadow: "0 2px 8px rgba(0,0,0,0.2)",
                  cursor: "pointer",
                  textDecoration: "none",
                }}
              >
                <span
                  style={{
                    display: "flex",
                    height: "28px",
                    width: "28px",
                    flexShrink: 0,
                    alignItems: "center",
                    justifyContent: "center",
                    borderRadius: "9999px",
                    backgroundColor: "rgba(45, 106, 93, 0.25)",
                    color: "#57AB5A",
                  }}
                >
                  {t.icon}
                </span>
                {t.label}
              </Tag>
            );
          })}
        </div>
      )}
    </section>
  );
}

export { CommunityOrbit as Component };
