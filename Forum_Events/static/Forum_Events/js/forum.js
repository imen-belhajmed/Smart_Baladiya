"use strict";

document.querySelectorAll("[data-event-carousel]").forEach((carousel) => {
  const track = carousel.querySelector("[data-event-track]");
  const slides = carousel.querySelectorAll("[data-event-slide]");
  const controls = carousel.parentElement.querySelector(".event-carousel-controls");
  if (!track || !controls || slides.length < 2) return;

  const previous = controls.querySelector("[data-event-previous]");
  const next = controls.querySelector("[data-event-next]");
  if (!previous || !next) return;

  let activeSlide = 0;
  const updateCarousel = () => {
    track.style.transform = `translateX(-${activeSlide * 100}%)`;
    previous.disabled = activeSlide === 0;
    next.disabled = activeSlide === slides.length - 1;
  };

  previous.addEventListener("click", () => {
    activeSlide -= 1;
    updateCarousel();
  });
  next.addEventListener("click", () => {
    activeSlide += 1;
    updateCarousel();
  });
});
