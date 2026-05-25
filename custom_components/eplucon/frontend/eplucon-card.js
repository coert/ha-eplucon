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
        return this.config?.variant === "both" ? 6 : 3;
    }

    getGridOptions() {
        return {
            columns: 6,
            rows: this.config?.variant === "both" ? 5 : 3,
            min_rows: 3,
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
            sections.push(`
        <section class="hero">
          <div class="eyebrow">${attrs.device_name || "Eplucon"}</div>
          <div class="headline">${this.formatTemperature(attrs.indoor_temperature)}</div>
          <div class="subline">
            <span>${attrs.operation_mode_text || stateObj.state}</span>
            <span>${this.formatTemperature(attrs.outdoor_temperature)} outside</span>
          </div>
        </section>
      `);
        }

        if (variant === "details" || variant === "both") {
            sections.push(`
        <section class="details">
          ${this.metric("Target", this.formatTemperature(attrs.configured_indoor_temperature))}
          ${this.metric("Boiler", this.formatTemperature(attrs.ww_temperature))}
          ${this.metric("Boiler Set", this.formatTemperature(attrs.ww_temperature_configured))}
          ${this.metric("Heating In", this.formatTemperature(attrs.heating_in_temperature))}
          ${this.metric("Heating Out", this.formatTemperature(attrs.heating_out_temperature))}
          ${this.metric("Brine In", this.formatTemperature(attrs.brine_in_temperature))}
          ${this.metric("Brine Out", this.formatTemperature(attrs.brine_out_temperature))}
          ${this.metric("Usage", this.formatEnergy(attrs.energy_usage))}
          ${this.metric("Delivered", this.formatEnergy(attrs.energy_delivered))}
          ${this.metric("SPF", this.formatValue(attrs.spf))}
        </section>
      `);
        }

        const updated = attrs.last_updated ? new Date(attrs.last_updated).toLocaleString() : "Unknown";

        this.innerHTML = `
      <ha-card>
        <div class="card-shell">
          ${sections.join("")}
          <footer class="footer">Updated ${updated}</footer>
        </div>
      </ha-card>
    `;
        this.applyStyles();
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
        --eplucon-panel: linear-gradient(135deg, #f6f2e8 0%, #d6e7e1 100%);
      }

      .card-shell {
        display: grid;
        gap: 16px;
        padding: 20px;
        background: var(--eplucon-panel);
        color: var(--eplucon-ink);
      }

      .hero {
        padding: 20px;
        border-radius: 18px;
        background: rgba(255, 255, 255, 0.72);
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.75);
      }

      .eyebrow {
        font-size: 0.78rem;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        opacity: 0.7;
      }

      .headline {
        margin-top: 8px;
        font-size: 2.8rem;
        line-height: 1;
        font-weight: 700;
      }

      .subline {
        display: flex;
        justify-content: space-between;
        gap: 12px;
        margin-top: 12px;
        font-size: 0.95rem;
      }

      .details {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 10px;
      }

      .metric {
        padding: 12px;
        border-radius: 14px;
        background: rgba(23, 49, 58, 0.08);
      }

      .metric-label {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        opacity: 0.7;
      }

      .metric-value {
        margin-top: 6px;
        font-size: 1.1rem;
        font-weight: 600;
      }

      .footer,
      .missing {
        font-size: 0.86rem;
        opacity: 0.72;
      }

      @media (max-width: 600px) {
        .card-shell {
          padding: 16px;
        }

        .headline {
          font-size: 2.2rem;
        }

        .subline {
          flex-direction: column;
        }
      }
    `;
        this.appendChild(style);
    }

    metric(label, value) {
        return `
      <div class="metric">
        <div class="metric-label">${label}</div>
        <div class="metric-value">${value}</div>
      </div>
    `;
    }

    formatTemperature(value) {
        return value === undefined || value === null ? "--" : `${value} °C`;
    }

    formatEnergy(value) {
        return value === undefined || value === null ? "--" : `${value} kWh`;
    }

    formatValue(value) {
        return value === undefined || value === null ? "--" : `${value}`;
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