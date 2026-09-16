import React from "react";
import { motion } from "framer-motion";
import { Star } from "lucide-react";

export function InfiniteFloatingTestimonials({ testimonials, speed = 35, direction = "left" }) {
  // Duplicate list to create a seamless infinite loop
  const duplicated = [...testimonials, ...testimonials];

  const animateX = direction === "left" ? ["0%", "-50%"] : ["-50%", "0%"];

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        overflow: "hidden",
        padding: "1.5rem 0",
        maskImage:
          "linear-gradient(to right, transparent, black 15%, black 85%, transparent 100%)",
        WebkitMaskImage:
          "linear-gradient(to right, transparent, black 15%, black 85%, transparent 100%)",
      }}
    >
      <motion.div
        style={{
          display: "flex",
          width: "max-content",
          gap: "1.5rem",
        }}
        animate={{
          x: animateX,
        }}
        transition={{
          ease: "linear",
          duration: speed,
          repeat: Infinity,
        }}
        whileHover={{ animationPlayState: "paused" }}
      >
        {duplicated.map((item, idx) => (
          <div
            key={idx}
            style={{
              width: "360px",
              flexShrink: 0,
              backgroundColor: "#161B22",
              border: "1px solid rgba(255, 255, 255, 0.1)",
              borderRadius: "20px",
              padding: "1.5rem",
              boxShadow: "0 8px 24px rgba(0, 0, 0, 0.25)",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
              transition: "transform 0.2s ease, border-color 0.2s ease",
            }}
          >
            {/* Rating Stars */}
            <div style={{ display: "flex", gap: "4px", marginBottom: "1rem" }}>
              {[...Array(5)].map((_, i) => (
                <Star
                  key={i}
                  size={16}
                  fill={i < (item.rating || 5) ? "#F59E0B" : "none"}
                  color="#F59E0B"
                />
              ))}
            </div>

            {/* Testimonial Quote */}
            <p
              style={{
                fontSize: "14px",
                lineHeight: "1.6",
                color: "#E6EDF3",
                margin: "0 0 1.25rem 0",
                fontStyle: "italic",
              }}
            >
              "{item.quote}"
            </p>

            {/* User Profile Info */}
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <img
                src={item.avatar}
                alt={item.name}
                style={{
                  width: "44px",
                  height: "44px",
                  borderRadius: "9999px",
                  objectFit: "cover",
                  border: "2px solid #2D6A5D",
                }}
              />
              <div>
                <div style={{ fontWeight: 600, fontSize: "14px", color: "#FFFFFF" }}>
                  {item.name}
                </div>
                <div style={{ fontSize: "12px", color: "rgba(255,255,255,0.6)" }}>
                  {item.role} • {item.hospital}
                </div>
              </div>
            </div>
          </div>
        ))}
      </motion.div>
    </div>
  );
}
