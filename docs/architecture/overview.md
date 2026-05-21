# Architecture Overview

SenarioSpark is organized around a simple MVP flow:

```text
video input
  -> AI understanding service
  -> structured content data
  -> Go backend storage and distribution
  -> mobile frontend highlight rendering
  -> interaction events back to backend
```

The Python AI service owns model-driven video understanding. The Go backend owns product APIs, persistence, distribution, and interaction stability. The frontend owns video playback and low-friction interaction rendering.

