import { useEffect } from "react";

export default function useScrollReveal() {
  useEffect(() => {
    const revealVisible = () => {
      const elements = document.querySelectorAll(".scroll-reveal:not(.is-visible)");
      if (!elements.length) return;

      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              entry.target.classList.add("is-visible");
              observer.unobserve(entry.target);
            }
          });
        },
        {
          threshold: 0.05,
          rootMargin: "0px 0px 50px 0px",
        }
      );

      elements.forEach((el) => {
        // If element is already in viewport or window scroll is past it, reveal immediately
        const rect = el.getBoundingClientRect();
        if (rect.top < window.innerHeight + 100) {
          el.classList.add("is-visible");
        } else {
          observer.observe(el);
        }
      });
    };

    revealVisible();
    const interval = setInterval(revealVisible, 500);

    return () => clearInterval(interval);
  }, []);
}
