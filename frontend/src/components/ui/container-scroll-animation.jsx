import React, { useRef, useState, useEffect } from "react";
import { useScroll, useTransform, motion } from "framer-motion";

export const ContainerScroll = ({ titleComponent, children }) => {
  const containerRef = useRef(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
  });
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => {
      window.removeEventListener("resize", checkMobile);
    };
  }, []);

  const scaleDimensions = () => {
    return isMobile ? [0.75, 0.92] : [1.05, 1];
  };

  const rotate = useTransform(scrollYProgress, [0, 1], [20, 0]);
  const scale = useTransform(scrollYProgress, [0, 1], scaleDimensions());
  const translate = useTransform(scrollYProgress, [0, 1], [0, -100]);

  return (
    <div
      ref={containerRef}
      style={{
        minHeight: isMobile ? "50rem" : "68rem",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        position: "relative",
        padding: isMobile ? "1rem" : "3rem 1.5rem",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          paddingTop: isMobile ? "2rem" : "5rem",
          paddingBottom: isMobile ? "3rem" : "6rem",
          width: "100%",
          position: "relative",
          perspective: "1000px",
        }}
      >
        <Header translate={translate} titleComponent={titleComponent} />
        <Card rotate={rotate} translate={translate} scale={scale}>
          {children}
        </Card>
      </div>
    </div>
  );
};

export const Header = ({ translate, titleComponent }) => {
  return (
    <motion.div
      style={{
        translateY: translate,
        maxWidth: "68rem",
        margin: "0 auto",
        textAlign: "center",
      }}
    >
      {titleComponent}
    </motion.div>
  );
};

export const Card = ({ rotate, scale, children }) => {
  return (
    <motion.div
      style={{
        rotateX: rotate,
        scale,
        boxShadow:
          "0 0 #0000004d, 0 10px 25px #0000003a, 0 40px 40px #00000028, 0 80px 60px #00000018",
        maxWidth: "68rem",
        marginTop: "-1rem",
        marginLeft: "auto",
        marginRight: "auto",
        height: "36rem",
        width: "100%",
        border: "3px solid #1E293B",
        padding: "1rem",
        backgroundColor: "#0B1320",
        borderRadius: "28px",
      }}
    >
      <div
        style={{
          height: "100%",
          width: "100%",
          overflow: "hidden",
          borderRadius: "20px",
          backgroundColor: "#0F172A",
          display: "flex",
          position: "relative",
        }}
      >
        {children}
      </div>
    </motion.div>
  );
};
