const ASSET_BASE_URL = "/eplucon_assets";

const ASSETS = {
  screen1: `${ASSET_BASE_URL}/screen1.jpg`,
  screen4: `${ASSET_BASE_URL}/screen4.svg`,
  modeIcons: {
    sun: `${ASSET_BASE_URL}/operation_mode_sun.svg`,
    snow: `${ASSET_BASE_URL}/operation_mode_snow.svg`,
  },
  temperature: `${ASSET_BASE_URL}/temperature-high.svg`,
};

class EpluconCard extends HTMLElement {
  static getStubConfig() {
    return {
      entity: "sensor.example_eplucon_dashboard_summary",
      variant: "both",
    };
  }

  static getConfigForm() {
    return {
      schema: [
        {
          name: "entity",
          required: true,
          selector: {
            entity: {
              domain: "sensor",
            },
          },
        },
        {
          name: "variant",
          required: true,
          selector: {
            select: {
              mode: "dropdown",
              options: [
                { value: "overview", label: "Overview" },
                { value: "details", label: "Details" },
                { value: "both", label: "Both" },
              ],
            },
          },
        },
      ],
    };
  }

  static get properties() {
    return {
      hass: {},
      config: {},
    };
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("You need to define a dashboard summary sensor.");
    }
    this.config = {
      variant: "both",
      ...config,
    };
  }

  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  getCardSize() {
    return this.config?.variant === "both" ? 10 : 5;
  }

  getGridOptions() {
    return {
      columns: "full",
      rows: this.config?.variant === "both" ? 10 : 5,
      min_rows: 4,
    };
  }

  render() {
    if (!this.config || !this._hass) {
      return;
    }

    const stateObj = this._hass.states[this.config.entity];
    if (!stateObj) {
      this.innerHTML = `
        <ha-card>
          <div class="missing">Entity ${this.config.entity} not found.</div>
        </ha-card>
      `;
      this.applyStyles();
      return;
    }

    const attrs = stateObj.attributes;
    const variant = this.config.variant || "both";
    const sections = [];

    if (variant === "overview" || variant === "both") {
      sections.push(this.renderOverviewScene(attrs, stateObj));
    }

    if (variant === "details" || variant === "both") {
      sections.push(this.renderDashboardScene(attrs));
    }

    const updated = attrs.last_updated
      ? new Date(attrs.last_updated).toLocaleString()
      : "Unknown";

    this.innerHTML = `
      <ha-card>
        <div class="card-shell">
          <header class="card-header">
            <div>
              <div class="eyebrow">${attrs.device_name || "Eplucon"}</div>
              <div class="header-title">Heat Pump Dashboard</div>
            </div>
            <div class="header-meta">Updated ${updated}</div>
          </header>
          ${sections.join("")}
        </div>
      </ha-card>
    `;
    this.applyStyles();
  }

  renderOverviewScene(attrs, stateObj) {
    const modeIcon = this.getModeIcon(attrs.operation_mode_icon);

    return `
      <section class="scene scene--overview">
        <img class="scene__asset" src="${ASSETS.screen4}" alt="Heat pump overview" />
        <div class="scene__overlay scene__overlay--overview">
          <div class="scene-topline">${attrs.last_updated ? new Date(attrs.last_updated).toLocaleString() : "Live data"}</div>
          <div class="mode-pill">
            ${modeIcon ? `<span class="mode-pill__icon-shell"><img class="mode-pill__icon" src="${modeIcon}" alt="" /></span>` : ""}
            <span class="mode-pill__text">${attrs.operation_mode_text || stateObj.state}</span>
          </div>
          <div class="temperature-callout">
            <img class="temperature-callout__icon" src="${ASSETS.temperature}" alt="" />
            <span>${this.formatTemperature(attrs.indoor_temperature)}</span>
          </div>
        </div>
      </section>
    `;
  }

  renderDashboardScene(attrs) {
    return `
      <section class="scene scene--details">
        <img class="scene__asset" src="${ASSETS.screen1}" alt="Heat pump detail dashboard" />
        <div class="scene__overlay scene__overlay--details">
          ${this.positionedMetric("details-outdoor", this.formatTemperature(attrs.outdoor_temperature))}

          <div class="details-center-stack">
            <div class="details-label details-label--green">Actueel</div>
            <div class="details-value details-value--green">${this.formatTemperature(attrs.indoor_temperature)}</div>
            <div class="details-label details-label--dark">Ingesteld</div>
            <div class="details-value details-value--dark">${this.formatTemperature(attrs.configured_indoor_temperature)}</div>
          </div>

          ${this.positionedLabel("details-boiler-label details-label--green", "Actueel boiler")}
          ${this.positionedMetric("details-boiler-value details-value--green", this.formatTemperature(attrs.ww_temperature))}
          ${this.positionedLabel("details-boiler-target-label details-label--dark", "Ingesteld boiler")}
          ${this.positionedMetric("details-boiler-target-value details-value--dark", this.formatTemperature(attrs.ww_temperature_configured))}

          ${this.positionedLabel("details-heating-label", "aanvoer")}
          ${this.positionedMetric("details-heating-in", this.formatTemperature(attrs.heating_in_temperature))}
          ${this.positionedMetric("details-heating-out", this.formatTemperature(attrs.heating_out_temperature))}

          ${this.positionedLabel("details-source-label", "bron")}
          ${this.positionedMetric("details-brine-in", this.formatTemperature(attrs.brine_in_temperature))}
          ${this.positionedMetric("details-brine-out", this.formatTemperature(attrs.brine_out_temperature))}

          ${this.positionedLabel("details-usage-label", "opgenomen energie")}
          ${this.positionedMetric("details-usage-value", this.formatEnergy(attrs.energy_usage))}
          ${this.positionedLabel("details-delivered-label details-label--dark", "geleverde energie")}
          ${this.positionedMetric("details-delivered-value details-value--green", this.formatEnergy(attrs.energy_delivered))}
          ${this.positionedLabel("details-spf-label", "spf")}
          ${this.positionedMetric("details-spf-value", this.formatValue(attrs.spf))}
        </div>
      </section>
    `;
  }

  railMetric(label, value) {
    return `
      <div class="rail-card">
        <div class="rail-card__label">${label}</div>
        <div class="rail-card__value">${value}</div>
      </div>
    `;
  }

  positionedLabel(className, text) {
    return `<div class="details-label ${className}">${text}</div>`;
  }

  positionedMetric(className, value) {
    return `<div class="details-value ${className}">${value}</div>`;
  }

  getModeIcon(iconKey) {
    return iconKey ? ASSETS.modeIcons[iconKey] || null : null;
  }

  applyStyles() {
    const styleId = "eplucon-card-style";
    if (this.querySelector(`#${styleId}`)) {
      return;
    }

    const style = document.createElement("style");
    style.id = styleId;
    style.textContent = `
      ha-card {
        --eplucon-accent: #1d7f62;
        --eplucon-ink: #17313a;
        --eplucon-soft: #f3efe3;
        --eplucon-panel: linear-gradient(160deg, #edf5f2 0%, #d7ebe2 42%, #f4efe1 100%);
        --eplucon-card-bg: rgba(10, 33, 45, 0.56);
        --eplucon-shadow: 0 20px 50px rgba(7, 34, 44, 0.22);
      }

      .card-shell {
        display: grid;
        gap: 18px;
        padding: 24px;
        background: var(--eplucon-panel);
        color: var(--eplucon-ink);
      }

      .card-header {
        display: flex;
        justify-content: space-between;
        align-items: end;
        gap: 16px;
      }

      .eyebrow {
        font-size: 0.78rem;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        opacity: 0.68;
      }

      .header-title {
        margin-top: 4px;
        font-size: 1.8rem;
        font-weight: 700;
      }

      .header-meta {
        font-size: 0.92rem;
        opacity: 0.72;
      }

      .scene {
        position: relative;
        overflow: hidden;
        border-radius: 28px;
        box-shadow: var(--eplucon-shadow);
        background: #d5e4ef;
      }

      .scene--overview {
        aspect-ratio: 16 / 9;
      }

      .scene--details {
        aspect-ratio: 1000 / 563;
      }

      .scene__asset {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        object-fit: cover;
      }

      .scene__overlay {
        position: absolute;
        inset: 0;
      }

      .scene-topline {
        position: absolute;
        top: 3.5%;
        left: 50%;
        transform: translateX(-50%);
        padding: 0.4rem 0.9rem;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.74);
        backdrop-filter: blur(8px);
        font-size: clamp(0.72rem, 1.2vw, 1rem);
        font-weight: 600;
      }

      .mode-pill {
        position: absolute;
        left: 34%;
        top: 81%;
        transform: translate(-50%, -50%);
        display: inline-flex;
        align-items: center;
        gap: 0.7rem;
        padding: 0.7rem 1.2rem;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.82);
        box-shadow: 0 14px 30px rgba(0, 0, 0, 0.14);
        font-size: clamp(0.8rem, 1.3vw, 1.2rem);
        font-weight: 700;
      }

      .mode-pill__icon-shell {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: clamp(28px, 3.8vw, 42px);
        height: clamp(28px, 3.8vw, 42px);
        border-radius: 999px;
        background: rgba(16, 72, 98, 0.18);
        box-shadow: inset 0 0 0 1px rgba(16, 72, 98, 0.12);
      }

      .mode-pill__icon {
        width: clamp(20px, 3vw, 34px);
        height: clamp(20px, 3vw, 34px);
        filter: drop-shadow(0 1px 2px rgba(8, 38, 54, 0.4));
      }

      .mode-pill__text {
        font-variant: small-caps;
        letter-spacing: 0.04em;
        text-transform: lowercase;
        color: #17313a;
      }

      .temperature-callout {
        position: absolute;
        left: 50%;
        top: 50%;
        transform: translate(-50%, -50%);
        display: inline-flex;
        align-items: center;
        gap: 0.8rem;
        padding: 0.85rem 1.4rem;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.86);
        box-shadow: 0 18px 42px rgba(0, 0, 0, 0.16);
        color: #11824a;
        font-size: clamp(1.1rem, 3vw, 2.9rem);
        font-weight: 800;
      }

      .temperature-callout__icon {
        width: clamp(26px, 4vw, 48px);
        height: clamp(26px, 4vw, 48px);
      }

      .details-label,
      .details-value {
        position: absolute;
        transform: translateX(-50%);
        text-align: center;
        font-weight: 700;
        text-shadow: 0 1px 4px rgba(0, 0, 0, 0.38);
        line-height: 1.15;
      }

      .details-label {
        font-size: clamp(0.8rem, 1.35vw, 1.5rem);
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: white;
      }

      .details-label--dark {
        color: #1f2937;
        text-shadow: 0 1px 3px rgba(255, 255, 255, 0.55);
      }

      .details-label--green {
        color: #16a34a;
        text-shadow: 0 1px 3px rgba(255, 255, 255, 0.5);
      }

      .details-value {
        font-size: clamp(1rem, 1.8vw, 2rem);
        color: white;
      }

      .details-value--dark {
        color: #1f2937;
        text-shadow: 0 1px 3px rgba(255, 255, 255, 0.62);
      }

      .details-value--green {
        color: #16a34a;
        text-shadow: 0 1px 3px rgba(255, 255, 255, 0.5);
      }

      .details-current-label,
      .details-current-value {
        transform: translate(-50%, -50%);
      }

      .details-center-stack {
        position: absolute;
        top: 45.4%;
        left: 43.2%;
        display: grid;
        gap: 0.12rem;
        text-align: left;
      }

      .details-center-stack .details-label,
      .details-center-stack .details-value {
        position: static;
        transform: none;
        text-align: left;
      }

      .details-heating-label,
      .details-source-label {
        font-size: clamp(0.95rem, 1.7vw, 2rem);
      }

      .details-outdoor,
      .details-heating-in,
      .details-heating-out,
      .details-brine-in,
      .details-brine-out,
      .details-usage-value,
      .details-delivered-value,
      .details-spf-value {
        font-size: clamp(1rem, 1.85vw, 2.1rem);
      }

      .details-usage-label,
      .details-delivered-label,
      .details-spf-label {
        font-size: clamp(0.76rem, 1.18vw, 1.3rem);
      }

      .details-outdoor { top: 31.1%; left: 68.75%; }
      .details-current-label { top: 46.2%; left: 46.9%; }
      .details-current-value { top: 50.1%; left: 46.9%; }
      .details-target-label { top: 53.0%; left: 46.9%; }
      .details-target-value { top: 56.8%; left: 46.9%; }
      .details-boiler-label { top: 72.8%; left: 57.9%; }
      .details-boiler-value { top: 76.6%; left: 61.3%; }
      .details-boiler-target-label { top: 82.8%; left: 57.3%; }
      .details-boiler-target-value { top: 86.6%; left: 62.5%; }
      .details-heating-label { top: 29.5%; left: 8.75%; }
      .details-heating-in { top: 37.1%; left: 10.6%; }
      .details-heating-out { top: 48.6%; left: 10.6%; }
      .details-source-label { top: 62.8%; left: 8.75%; }
      .details-brine-in { top: 72.6%; left: 11.3%; }
      .details-brine-out { top: 84.1%; left: 11.3%; }
      .details-usage-label { top: 29.3%; left: 89.4%; }
      .details-usage-value { top: 38.2%; left: 89.4%; }
      .details-delivered-label { top: 52.2%; left: 89.4%; }
      .details-delivered-value { top: 61.1%; left: 89.4%; }
      .details-spf-label { top: 77.3%; left: 89.4%; }
      .details-spf-value { top: 81.7%; left: 89.4%; }

      .missing {
        padding: 1rem;
        font-size: 0.86rem;
        opacity: 0.72;
      }

      @media (max-width: 900px) {
        .card-shell {
          padding: 16px;
        }

        .card-header {
          align-items: start;
          flex-direction: column;
        }

        .scene-topline {
          padding: 0.35rem 0.75rem;
          font-size: clamp(0.68rem, 1vw, 0.88rem);
        }

        .mode-pill {
          gap: 0.5rem;
          padding: 0.55rem 0.95rem;
          font-size: clamp(0.74rem, 1vw, 0.98rem);
        }

        .mode-pill__icon-shell {
          width: clamp(24px, 3vw, 34px);
          height: clamp(24px, 3vw, 34px);
        }

        .mode-pill__icon {
          width: clamp(16px, 2.2vw, 24px);
          height: clamp(16px, 2.2vw, 24px);
        }

        .temperature-callout {
          gap: 0.55rem;
          padding: 0.7rem 1.1rem;
          font-size: clamp(0.98rem, 2vw, 2rem);
        }

        .temperature-callout__icon {
          width: clamp(22px, 3vw, 34px);
          height: clamp(22px, 3vw, 34px);
        }
      }

      @media (max-width: 680px) {
        .scene-topline {
          padding: 0.28rem 0.62rem;
          font-size: 0.66rem;
        }

        .mode-pill {
          gap: 0.42rem;
          padding: 0.44rem 0.78rem;
          font-size: 0.7rem;
        }

        .mode-pill__icon-shell {
          width: 22px;
          height: 22px;
        }

        .mode-pill__icon {
          width: 14px;
          height: 14px;
        }

        .temperature-callout {
          gap: 0.45rem;
          padding: 0.58rem 0.92rem;
          font-size: clamp(0.88rem, 2.2vw, 1.4rem);
        }

        .temperature-callout__icon {
          width: 18px;
          height: 18px;
        }

        .scene--details {
          overflow-x: auto;
        }

        .details-label,
        .details-value {
          font-size: clamp(0.58rem, 1.8vw, 0.95rem);
        }
      }
    `;
    this.appendChild(style);
  }

  formatTemperature(value) {
    return value === undefined || value === null ? "--" : `${this.formatNumber(value)} °C`;
  }

  formatEnergy(value) {
    return value === undefined || value === null ? "--" : `${this.formatNumber(value)} kWh`;
  }

  formatValue(value) {
    return value === undefined || value === null ? "--" : `${this.formatNumber(value)}`;
  }

  formatNumber(value) {
    if (typeof value !== "number") {
      return value;
    }

    return new Intl.NumberFormat(undefined, {
      maximumFractionDigits: Number.isInteger(value) ? 0 : 1,
    }).format(value);
  }
}

customElements.define("eplucon-card", EpluconCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "eplucon-card",
  name: "Eplucon",
  description: "Dashboard card for Eplucon heat pump summary sensors.",
  preview: true,
});