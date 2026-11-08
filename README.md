# DABOIT-BCI-1

### Total Artificial Synesthesia Architecture

> A proprietary, bi-directional Brain-Computer Interface (BCI) architecture, together with its reference simulation suite.

**Project Code:** DABOIT-BCI-1 (Revised Edition, Multi-Sensory System Integration)
**Author:** João Paulo Daboit
**Last updated:** July 2026
**Status:** Conceptual architecture + software simulators (no physical hardware exists)

---

## ⚠️ Intellectual Property Notice

**DABOIT-BCI-1 is not free or open technology.**

Copyright © 2026 João Paulo Daboit. **All rights reserved.**

The DABOIT-BCI-1 architecture, including its hardware topology, cortical mapping scheme, sensory-injection model, "Cacos" programming paradigm, corporate/business model, documentation, source code, and associated names and branding, is the original, proprietary work of the author and is protected by copyright.

This repository is published for **viewing and evaluation purposes only**. No license, express or implied, is granted. Specifically, without prior written permission from the author, you may **not**:

- copy, modify, merge, publish, distribute, sublicense, or sell any part of this work;
- build, manufacture, or commercialize hardware, software, or services based on this architecture;
- create derivative works, forks for redistribution, or competing implementations derived from it;
- use the name "DABOIT-BCI" or any confusingly similar name.

For licensing, partnership, or commercial inquiries, contact the author directly.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [About the BCI](#2-about-the-bci)
3. [Hardware Architecture](#3-hardware-architecture)
4. [Cortical Mapping](#4-cortical-mapping)
5. [Business Model](#5-business-model)
6. [Simulation Suite](#6-simulation-suite)
7. [Installation and Usage](#7-installation-and-usage)
8. [Safety and Security Notes](#8-safety-and-security-notes)
9. [Disclaimer](#9-disclaimer)
10. [License and Contact](#10-license-and-contact)

---

## 1. Executive Summary

DABOIT-BCI-1 is a high-density, bi-directional Brain-Computer Interface designed to deliver **Total Artificial Synesthesia**: the interception, decoding, and injection of digital data streams directly to and from the human cortex, bypassing the biological sensory organs.

The central engineering idea is a **hardware-segregated topology**. Heavy computation and heat dissipation live in an external, cranially anchored socket, while only a thin graphene mesh touches neural tissue. By pairing this split with a non-thermal conductive layer, the design targets multi-sensory stimulation without the tissue-heating problem that has historically limited electrical stimulation.

This repository contains the architecture specification and two software simulators that let the design be explored, tested, and demonstrated before any physical deployment.

---

## 2. About the BCI

### What it is

A BCI is a system that creates a direct communication pathway between the brain and an external device. DABOIT-BCI-1 is **bi-directional**:

| Direction | Mode | Function |
|---|---|---|
| Brain → Machine | **Read (Capture)** | Monitors raw micro-voltage fluctuations (µV) at each electrode node and relays them to the central AI socket. |
| Machine → Brain | **Write (Injection)** | Delivers coordinated micro-current pulses into specified cortical layers to induce artificial sensory perception. |

### Key design principles

- **Thermal segregation.** Processing happens outside the body; the cortical interface is passive and non-thermal by design.
- **Full-cortex coverage.** A continuous, gapless hexagonal mesh eliminates dead zones across the targeted lobes.
- **User sovereignty.** A purely analog, hardwired mechanical kill switch gives the user absolute control, independent of any software.
- **Five-sense core, extensible beyond.** Vision, hearing, touch, smell, and taste form the core mapping; the Lab simulator extends this to 14 sensory channels.
- **Shared experience.** An encrypted peer-to-peer protocol allows sessional sharing of sensory streams between users or with autonomous robotic units.

### Why it is proprietary

The value of DABOIT-BCI-1 lies in the integration of its parts: the segregated topology, the mesh geometry and addressing scheme, the cortical sector mapping, the sensory-programming model, and the two-entity business structure. These are the author's original work and are protected accordingly. Public visibility of this repository does **not** make the technology open source.

---

## 3. Hardware Architecture

The system is split into two environments to isolate heat dissipation from sensitive neural tissue.

### 3.1 Cranial Anchored Neural Socket (External Processing Zone)

*Location: occipital/nuchal region, anchored to the cranial base with an external-facing interface.*

| Component | Description |
|---|---|
| **Central AI Engine** | Local deep-learning models that decode raw neural voltage and encode incoming streams. Orchestrates the user's personal synesthetic matrix map (estimated **24-month calibration period**). Heat is dissipated outward into the environment. |
| **Local Nanometric Storage ("Cacos")** | Physical expansion slots for high-speed nanometric memory modules holding raw sensory streams: high-fidelity audio, texturized volumetric files, chemical volatile matrices, and video. |
| **Power Management** | Micro solid-state battery arrays recharged by ultra-low-frequency electromagnetic induction. |
| **Mechanical Circuit Breaker (Kill Switch)** | Physical, analog, hardwired switch on the main power rail. Instantly isolates the brain from software exploits, logic loops, or hostile sensory overload. |
| **Telecom Networking Module** | Integrated transceiver running a dedicated, encrypted P2P protocol over IP. Routes decoded sensory data to another user's socket ID or to an autonomous humanoid robotic unit. |

### 3.2 Moldable Global Mesh (Biological Interface Zone)

| Property | Description |
|---|---|
| **Matrix geometry** | Continuous, gapless hexagonal array covering the entire cerebral cortex. |
| **Conduction substrate** | High-purity single-layer graphene electrode nodes; low-impedance, targeting zero heat generation (non-thermal, 0.0 W) at the cortex during high-frequency firing. |
| **Addressing** | Synchronous logical bus; each hexagonal node has a unique integer coordinate ID. |
| **Node modes** | Write (injection) and Read (capture), selectable per node. |
| **Biocompatibility** | Biomimetic conductive hydrogel coating that buffers the tissue interface and is intended to prevent immune rejection and glial encapsulation. |

---

## 4. Cortical Mapping

The external AI translates binary packages from the "Caco" memory banks into spatial-temporal electrical signals, injected into five sectors of the graphene mesh:

| Sector | Sense | Target | Effect |
|---|---|---|---|
| **Occipital** | Vision ("Mental Cinema") | Primary visual cortex (V1) | High-definition streams modulating light, form, color, and depth, even with eyes closed. |
| **Temporal** | Hearing ("Holographic Audio") | Auditory cortex | Multi-frequency sound fields with absolute 3D positioning, with no external speakers. |
| **Parietal** | Touch and proprioception ("Haptic Mesh") | Somatosensory cortex | Textures, resistance, thermal variation, and calculated, safe pain feedback. |
| **Orbitofrontal & Piriform** | Smell ("Chemical Volatile Spectrum") | Primary olfactory cortex | Digital molecular signatures mapped to node activations, recreating complex aromas. |
| **Anterior Insular & Opercular** | Taste ("Taste Matrix") | Gustatory cortex | Coordinate patterns for the five basic tastes: sweet, salty, bitter, sour, umami. |

---

## 5. Business Model

The system is organized as a vertically integrated holding split into two entities, separating intellectual property from operational risk.

**Company A: Hardware & Manufacturing.** Holds all foundational engineering IP. Responsible for mass production of the graphene mesh, solid-state cranial sockets, bio-chips, and haptic/robotic integration layers.

**Company B: Telecom & Infrastructure.** Operates the global data architecture: regional low-latency edge servers, sensory stream routing, and the secure IP mesh network. Operates under a **SaaS** model with monthly subscription fees for real-time neural data traffic and P2P communication.

---

## 6. Simulation Suite

Two independent simulators let you evaluate the specification in software.

### 6.1 `daboit_bci_game.py`: Synesthetic Simulator (desktop)

A two-window, two-process desktop simulation built with **Python, NumPy, and PyGame**, following a strict *no-API* philosophy: rendering, matrix math, and audio are all built from first principles.

- **Window 1 (Game):** three interactive scenarios: *Drinking wine*, *Running on the beach*, *Riding a motorcycle*. User actions generate sensory spikes across the five core senses, packaged at 30 packets per second.
- **Window 2 (Brain):** a rotatable 3D cortex with the hexagonal graphene electrode mesh. Electrodes in each sector fire in response to the game, with an attention-like wave that propagates pulses to neighbouring nodes probabilistically, rendered at 60 FPS.

**Technical highlights**

- **True multiprocessing:** two OS processes (`spawn` context) communicating through a thread-safe `mp.Queue`, preventing frame drops.
- **Procedural 3D cortex:** a vectorized 3,000-point cloud with sulci and gyri modeled by continuous sinusoidal noise.
- **Custom projection pipeline:** yaw/pitch rotation matrices, depth sorting via `np.argsort`, and perspective scaling, with no graphics engine.
- **Algorithmic audio:** sounds (engine rumble, impacts) synthesized in RAM using `np.convolve` low-pass filtering, with no external audio assets.

### 6.2 `bci_lab.py`: DABOIT-BCI Lab v2.6 (web, mobile-friendly)

A zero-dependency (**Python standard library only**) local web app where you **program your own "Cacos"** and watch the simulated brain react in real time. It works on a phone (Pydroid 3, Termux, Pythonista) or on a PC with a phone on the same Wi-Fi.

- **14 sensory channels:** vision, hearing, touch, smell, taste, balance, temperature, proprioception, pain, heartbeat, hunger/thirst, time sense, compass, and radar.
- **Two programming modes:**
  - *Simple mode:* one line per item, evaluated 30 times per second in a restricted expression sandbox.
  - *Python mode:* full Python via `def quadro(c):`, with optional `inicio(c)`, buttons, HUD, and chat output.
- **Estimated mental state:** focus, calm, euphoria, stress, and immersion, derived from a deliberately simple fictional model.
- **Built-in safety simulation:** sensory inertia, neural adaptation, cross-contamination between senses, an overload limit, and a virtual circuit breaker that trips when the total load stays too high.
- **Built-in examples:** reaction game, motorcycle game, and a Python rhythm example. Cacos can be saved locally.

---

## 7. Installation and Usage

### 7.1 Desktop Simulator

**Prerequisites (Debian/Ubuntu/Kubuntu):**

```bash
sudo apt update
sudo apt install python3-venv python3-tk
```

**Isolated environment** (required on distributions implementing PEP 668):

```bash
cd /path/to/project
python3 -m venv env
source env/bin/activate
pip install --upgrade pip
pip install numpy pygame
```

**Run:**

```bash
python3 daboit_bci_game.py
```

| Window | Controls |
|---|---|
| Game | `1` / `2` / `3` select scenario · `ESC` back to menu · `K` kill switch |
| Brain | Mouse drag rotates · mouse wheel zooms · `SPACE` toggles auto-rotation |

### 7.2 Web Lab

No installation needed beyond Python 3.

```bash
python3 bci_lab.py            # this device only, http://localhost:8000
python3 bci_lab.py 9000       # custom port
python3 bci_lab.py --rede     # allow other devices on your Wi-Fi (PIN required for Python mode)
```

---

## 8. Safety and Security Notes

- **Python mode executes arbitrary code** with the permissions of the script on your device. Run only code you trust.
- By default the Lab server listens on **localhost only**. With `--rede`, Python mode requires the **PIN** printed in the terminal. Use `--rede` only on networks you trust.
- The kill switch (`K` in the desktop simulator, "Disjuntor" in the Lab) is part of the specification's safety philosophy: the user must always be able to cut the stream instantly.

---

## 9. Disclaimer

DABOIT-BCI-1 is a **conceptual architecture**. The simulators are **fictional models with no clinical or scientific validation**. Nothing in this repository affects a real person, and none of it constitutes medical advice or a medical device. Figures such as "0.0 W dissipation" and "24-month calibration" are design targets of the concept, not measured results. Any physical implementation would require extensive neuroscience, materials, safety, and regulatory work.

---

## 10. License and Contact

**Copyright © 2026 João Paulo Daboit. All rights reserved.**

This work is proprietary. No permission is granted to use, copy, modify, or distribute it except as explicitly agreed in writing by the author. For licensing or partnership inquiries, please contact the author.
