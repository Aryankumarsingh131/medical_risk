import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Mail, Phone, Award } from "lucide-react";

/**
 * InformationDrawer
 * 
 * Exact UX matching the user reference:
 * - Portrait photo cards with aspect ratio [3:4 / tall].
 * - Black & white or slightly dimmed by default, reveals full color on hover.
 * - Clicking a card slides open a right-side drawer window with:
 *     - (X) close button on top-left
 *     - Item index counter (e.g. 1/5) on top-right
 *     - Top horizontal line divider
 *     - Rounded portrait photo on the left
 *     - Name in large bold typography and subtitle/role below it on the right
 *     - Clean bio / description below
 * - Color theme: Deep dark palette (#111111, #161B22, #0D1520) matching system aesthetics.
 */
export default function InformationDrawer({
  title = "The People Behind It",
  description = "Tap a card to read who they are and what they actually work on.",
  items = [],
  backgroundColor = "#111111",
  textColor = "#f5f5f5",
  sidebarWidth = "50%",
  overlayOpacity = 0.45,
  emptyMessage = "No profiles available to display.",
}) {
  const [selectedIndex, setSelectedIndex] = useState(null);
  const [hoveredId, setHoveredId] = useState(null);

  const selectedItem = selectedIndex !== null ? items[selectedIndex] : null;

  return (
    <div
      style={{
        width: "100%",
        padding: "1.5rem 0",
        position: "relative",
      }}
    >
      {/* Section Heading & Subtitle matching reference */}
      <div style={{ marginBottom: "1.75rem" }}>
        <h2
          style={{
            margin: "0 0 0.5rem 0",
            fontSize: "clamp(1.5rem, 2.8vw, 2.2rem)",
            fontWeight: 800,
            letterSpacing: "-0.02em",
            textTransform: "uppercase",
            color: textColor,
          }}
        >
          {title}
        </h2>
        {description && (
          <p
            style={{
              margin: 0,
              fontSize: "0.95rem",
              color: "rgba(245, 245, 245, 0.7)",
              lineHeight: 1.5,
              maxWidth: "680px",
            }}
          >
            {description}
          </p>
        )}
      </div>

      {/* Grid of Tall Portrait Cards */}
      {items.length === 0 ? (
        <div
          style={{
            padding: "2.5rem",
            textAlign: "center",
            backgroundColor: "rgba(255,255,255,0.03)",
            borderRadius: "12px",
            border: "1px dashed rgba(255,255,255,0.15)",
            color: "rgba(255,255,255,0.5)",
            fontSize: "0.9rem",
          }}
        >
          {emptyMessage}
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
            gap: "20px",
          }}
        >
          {items.map((item, idx) => {
            const isHovered = hoveredId === item.id;
            return (
              <motion.div
                key={item.id}
                onMouseEnter={() => setHoveredId(item.id)}
                onMouseLeave={() => setHoveredId(null)}
                onClick={() => setSelectedIndex(idx)}
                whileHover={{ y: -6 }}
                transition={{ duration: 0.25 }}
                style={{
                  position: "relative",
                  cursor: "pointer",
                  borderRadius: "14px",
                  overflow: "hidden",
                  backgroundColor: "#0B111A",
                  border: isHovered
                    ? "2px solid #1AAB9B"
                    : "1px solid rgba(255, 255, 255, 0.12)",
                  boxShadow: isHovered
                    ? "0 14px 32px rgba(26, 171, 155, 0.3)"
                    : "0 4px 16px rgba(0,0,0,0.3)",
                  transition: "border-color 0.25s ease, box-shadow 0.25s ease",
                  aspectRatio: "3 / 4",
                }}
              >
                {/* Full-bleed Portrait Photo */}
                <img
                  src={
                    item.image ||
                    (item.role === "patient"
                      ? "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&q=80&w=600"
                      : "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?auto=format&fit=crop&q=80&w=600")
                  }
                  alt={item.name}
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "cover",
                    filter: isHovered ? "grayscale(0%)" : "grayscale(25%)",
                    transform: isHovered ? "scale(1.04)" : "scale(1)",
                    transition: "transform 0.4s ease, filter 0.4s ease",
                  }}
                />

                {/* Subtle gradient overlay at bottom with name */}
                <div
                  style={{
                    position: "absolute",
                    inset: 0,
                    background:
                      "linear-gradient(to top, rgba(10, 15, 25, 0.92) 0%, rgba(10, 15, 25, 0.3) 35%, transparent 70%)",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "flex-end",
                    padding: "16px",
                  }}
                >
                  <div
                    style={{
                      fontSize: "1.1rem",
                      fontWeight: 700,
                      color: "#FFFFFF",
                      lineHeight: 1.2,
                    }}
                  >
                    {item.role === "doctor" ? `Dr. ${item.name}` : item.name}
                  </div>
                  <div
                    style={{
                      fontSize: "0.8rem",
                      color: "#1AAB9B",
                      fontWeight: 600,
                      marginTop: "4px",
                    }}
                  >
                    {item.subtitle || item.specialization || "Active Patient"}
                  </div>

                  {/* Hover hint */}
                  <div
                    style={{
                      fontSize: "0.72rem",
                      color: isHovered ? "#C6F135" : "rgba(255,255,255,0.6)",
                      marginTop: "6px",
                      transition: "color 0.2s ease",
                    }}
                  >
                    {isHovered ? "Click to open drawer →" : "Click to view details"}
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}

      {/* Right-Side Sliding Information Drawer matching reference photo */}
      <AnimatePresence>
        {selectedItem && (
          <>
            {/* Backdrop Overlay */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: overlayOpacity }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedIndex(null)}
              style={{
                position: "fixed",
                inset: 0,
                backgroundColor: "#000000",
                zIndex: 9998,
              }}
            />

            {/* Sliding Drawer Container */}
            <motion.div
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", damping: 30, stiffness: 300 }}
              style={{
                position: "fixed",
                top: 0,
                right: 0,
                bottom: 0,
                width: sidebarWidth,
                minWidth: "340px",
                maxWidth: "620px",
                backgroundColor: backgroundColor,
                color: textColor,
                zIndex: 9999,
                boxShadow: "-12px 0 45px rgba(0,0,0,0.75)",
                display: "flex",
                flexDirection: "column",
                overflowY: "auto",
                borderLeft: "1px solid rgba(255,255,255,0.15)",
                padding: "2rem",
              }}
            >
              {/* Top Bar: Close Button (X) on left, Index Counter (e.g. 1/5) on right */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  marginBottom: "1.5rem",
                }}
              >
                <button
                  onClick={() => setSelectedIndex(null)}
                  style={{
                    background: "rgba(255,255,255,0.1)",
                    border: "1px solid rgba(255,255,255,0.15)",
                    borderRadius: "50%",
                    width: "38px",
                    height: "38px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#FFFFFF",
                    cursor: "pointer",
                    transition: "background 0.2s",
                  }}
                  title="Close"
                >
                  <X size={20} />
                </button>

                <div
                  style={{
                    fontSize: "0.95rem",
                    fontWeight: 600,
                    color: "rgba(255,255,255,0.6)",
                    letterSpacing: "0.05em",
                  }}
                >
                  {selectedIndex + 1}/{items.length}
                </div>
              </div>

              {/* Horizontal line divider matching reference */}
              <div
                style={{
                  width: "100%",
                  height: "1px",
                  backgroundColor: "rgba(255, 255, 255, 0.2)",
                  marginBottom: "2rem",
                }}
              />

              {/* Profile Card Header: Rounded Photo on left, Name & Role on right */}
              <div
                style={{
                  display: "flex",
                  gap: "24px",
                  alignItems: "center",
                  marginBottom: "2rem",
                }}
              >
                <div
                  style={{
                    width: "160px",
                    height: "190px",
                    flexShrink: 0,
                    borderRadius: "18px",
                    overflow: "hidden",
                    border: "2px solid rgba(255,255,255,0.15)",
                  }}
                >
                  <img
                    src={
                      selectedItem.image ||
                      (selectedItem.role === "patient"
                        ? "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&q=80&w=600"
                        : "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?auto=format&fit=crop&q=80&w=600")
                    }
                    alt={selectedItem.name}
                    style={{
                      width: "100%",
                      height: "100%",
                      objectFit: "cover",
                    }}
                  />
                </div>

                <div style={{ flex: 1 }}>
                  <h1
                    style={{
                      margin: "0 0 8px 0",
                      fontSize: "clamp(1.5rem, 2.5vw, 2.2rem)",
                      fontWeight: 800,
                      lineHeight: 1.15,
                      color: "#FFFFFF",
                    }}
                  >
                    {selectedItem.role === "doctor" ? `Dr. ${selectedItem.name}` : selectedItem.name}
                  </h1>
                  <div
                    style={{
                      fontSize: "1rem",
                      fontWeight: 600,
                      color: "#1AAB9B",
                      marginBottom: "6px",
                    }}
                  >
                    {selectedItem.subtitle || selectedItem.specialization || (selectedItem.role === "patient" ? "Patient" : "Medical Specialist")}
                  </div>
                  <div
                    style={{
                      fontSize: "0.85rem",
                      color: "rgba(255,255,255,0.55)",
                    }}
                  >
                    {selectedItem.hospital || "Apex Healthcare Hospital Network"}
                  </div>
                </div>
              </div>

              {/* Bio / Description paragraph below */}
              <div style={{ marginBottom: "2rem" }}>
                <p
                  style={{
                    fontSize: "0.95rem",
                    lineHeight: "1.7",
                    color: "rgba(255, 255, 255, 0.85)",
                    margin: 0,
                  }}
                >
                  {selectedItem.description ||
                    (selectedItem.role === "doctor"
                      ? "Specialized clinician focused on preventative cardiology, diagnostics, and transparent AI-assisted clinical workflows."
                      : "Active patient enrolled in preventative cardiovascular monitoring with personalized risk management.")}
                </p>
              </div>

              {/* Key Credentials / Attributes */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
                  gap: "12px",
                  marginBottom: "2rem",
                }}
              >
                {selectedItem.role === "doctor" ? (
                  <>
                    <div
                      style={{
                        backgroundColor: "rgba(255,255,255,0.04)",
                        border: "1px solid rgba(255,255,255,0.08)",
                        borderRadius: "12px",
                        padding: "12px",
                      }}
                    >
                      <div style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)" }}>Experience</div>
                      <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "#C6F135" }}>
                        {selectedItem.years_of_experience ? `${selectedItem.years_of_experience} Years` : "Senior Staff"}
                      </div>
                    </div>
                    <div
                      style={{
                        backgroundColor: "rgba(255,255,255,0.04)",
                        border: "1px solid rgba(255,255,255,0.08)",
                        borderRadius: "12px",
                        padding: "12px",
                      }}
                    >
                      <div style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)" }}>License</div>
                      <div style={{ fontSize: "0.95rem", fontWeight: 700, color: "#FFFFFF" }}>
                        {selectedItem.license_number || "REG-IN-2024"}
                      </div>
                    </div>
                    <div
                      style={{
                        backgroundColor: "rgba(255,255,255,0.04)",
                        border: "1px solid rgba(255,255,255,0.08)",
                        borderRadius: "12px",
                        padding: "12px",
                      }}
                    >
                      <div style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)" }}>Degree</div>
                      <div style={{ fontSize: "0.95rem", fontWeight: 700, color: "#FFFFFF" }}>
                        {selectedItem.degree || "MBBS, MD"}
                      </div>
                    </div>
                  </>
                ) : (
                  <>
                    <div
                      style={{
                        backgroundColor: "rgba(255,255,255,0.04)",
                        border: "1px solid rgba(255,255,255,0.08)",
                        borderRadius: "12px",
                        padding: "12px",
                      }}
                    >
                      <div style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)" }}>Age / Sex</div>
                      <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "#C6F135" }}>
                        {selectedItem.age ? `${selectedItem.age} yrs` : "Adult"}
                      </div>
                    </div>
                    <div
                      style={{
                        backgroundColor: "rgba(255,255,255,0.04)",
                        border: "1px solid rgba(255,255,255,0.08)",
                        borderRadius: "12px",
                        padding: "12px",
                      }}
                    >
                      <div style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)" }}>Assigned Doctor</div>
                      <div style={{ fontSize: "0.95rem", fontWeight: 700, color: "#FFFFFF" }}>
                        {selectedItem.assigned_doctor ? `Dr. ${selectedItem.assigned_doctor}` : "Assigned"}
                      </div>
                    </div>
                    <div
                      style={{
                        backgroundColor: "rgba(255,255,255,0.04)",
                        border: "1px solid rgba(255,255,255,0.08)",
                        borderRadius: "12px",
                        padding: "12px",
                      }}
                    >
                      <div style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)" }}>Status</div>
                      <div style={{ fontSize: "0.95rem", fontWeight: 700, color: "#3FB950" }}>
                        Active
                      </div>
                    </div>
                  </>
                )}
              </div>

              {/* Contacts / Quick Info */}
              <div
                style={{
                  backgroundColor: "rgba(255,255,255,0.03)",
                  border: "1px solid rgba(255,255,255,0.08)",
                  borderRadius: "14px",
                  padding: "1rem",
                  display: "flex",
                  flexDirection: "column",
                  gap: "10px",
                  marginTop: "auto",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "0.85rem" }}>
                  <Mail size={16} color="#1AAB9B" />
                  <span>{selectedItem.email || "Confidential on file"}</span>
                </div>
                {selectedItem.phone_number && (
                  <div style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "0.85rem" }}>
                    <Phone size={16} color="#1AAB9B" />
                    <span>{selectedItem.phone_number}</span>
                  </div>
                )}
                {selectedItem.certifications && (
                  <div style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "0.85rem" }}>
                    <Award size={16} color="#C6F135" />
                    <span>{selectedItem.certifications}</span>
                  </div>
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
