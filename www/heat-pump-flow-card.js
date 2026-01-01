/**
 * Heat Pump Flow Card for Home Assistant
 * Visualizes heat pump water flow with animated pipes and temperature gradients
 * 
 * Based on jasipsw/heat-pump-flow-card
 * Adapted for Neore heat pump integration
 */

class HeatPumpFlowCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._hass = null;
    this._config = null;
    this._animationFrame = null;
    this._dots = [];
  }

  setConfig(config) {
    if (!config.heat_pump) {
      throw new Error('You need to define heat_pump section');
    }

    this._config = {
      title: config.title || 'Heat Pump Flow',
      heat_pump: config.heat_pump || {},
      heat_pump_visual: {
        off_color: '#95a5a6',
        heating_color: '#e74c3c',
        cooling_color: '#3498db',
        dhw_color: '#e67e22',
        defrost_color: '#f1c40f',
        show_metrics: true,
        animate_fan: true,
        ...(config.heat_pump_visual || {})
      },
      buffer_tank: config.buffer_tank || null,
      dhw_tank: config.dhw_tank || null,
      hvac: config.hvac || null,
      animation: {
        enabled: true,
        min_flow_rate: 5,
        max_flow_rate: 1,
        max_flow_rate_value: 50,
        idle_threshold: 0,
        dot_size: 1.5,
        use_temp_color: false,
        dot_color: 'rgba(255, 255, 255, 0.75)',
        dot_opacity: 1.0,
        ...(config.animation || {})
      },
      temperature: {
        delta_threshold: 10,
        hot_color: '#e74c3c',
        cold_color: '#3498db',
        neutral_color: '#95a5a6',
        unit: 'C',
        ...(config.temperature || {})
      },
      temperature_status: {
        enabled: true,
        circle_radius: 12,
        points: {
          hp_outlet: { enabled: true },
          hp_inlet: { enabled: true },
          buffer_supply: { enabled: true },
          buffer_return: { enabled: true },
          hvac_supply: { enabled: true },
          hvac_return: { enabled: true },
          ...(config.temperature_status?.points || {})
        },
        ...(config.temperature_status || {})
      },
      text_style: {
        font_family: 'Courier New, monospace',
        font_size: 11,
        font_weight: 'bold',
        show_labels: false,
        ...(config.text_style || {})
      },
      display: {
        show_values: true,
        show_labels: true,
        show_icons: true,
        compact: false,
        decimal_places: 1,
        ...(config.display || {})
      }
    };

    this.render();
  }

  set hass(hass) {
    this._hass = hass;
    this.updateCard();
  }

  getCardSize() {
    return 6;
  }

  updateCard() {
    if (!this._hass || !this._config) return;

    // Update all dynamic values
    this.updateMetrics();
    this.updateTemperatures();
    this.updateColors();
    this.updateAnimation();
  }

  getEntityValue(entityId) {
    if (!entityId || !this._hass) return null;
    const entity = this._hass.states[entityId];
    return entity ? parseFloat(entity.state) : null;
  }

  getEntityState(entityId) {
    if (!entityId || !this._hass) return null;
    const entity = this._hass.states[entityId];
    return entity ? entity.state : null;
  }

  getEntityUnit(entityId) {
    if (!entityId || !this._hass) return '';
    const entity = this._hass.states[entityId];
    return entity?.attributes?.unit_of_measurement || '';
  }

  updateMetrics() {
    const hp = this._config.heat_pump;
    
    // Update power
    const power = this.getEntityValue(hp.power_entity);
    const powerEl = this.shadowRoot.querySelector('#power-value');
    if (powerEl && power !== null) {
      powerEl.textContent = `${power.toFixed(1)} ${this.getEntityUnit(hp.power_entity)}`;
    }

    // Update thermal output
    const thermal = this.getEntityValue(hp.thermal_entity);
    const thermalEl = this.shadowRoot.querySelector('#thermal-value');
    if (thermalEl && thermal !== null) {
      thermalEl.textContent = `${thermal.toFixed(1)} ${this.getEntityUnit(hp.thermal_entity)}`;
    }

    // Update COP
    const cop = this.getEntityValue(hp.cop_entity);
    const copEl = this.shadowRoot.querySelector('#cop-value');
    if (copEl && cop !== null) {
      copEl.textContent = cop.toFixed(2);
    }

    // Update flow rate
    const flow = this.getEntityValue(hp.flow_rate_entity);
    const flowEl = this.shadowRoot.querySelector('#flow-value');
    if (flowEl && flow !== null) {
      flowEl.textContent = `${flow.toFixed(2)} ${this.getEntityUnit(hp.flow_rate_entity)}`;
    }
  }

  updateTemperatures() {
    const hp = this._config.heat_pump;
    
    // Update outlet temperature
    const outletTemp = this.getEntityValue(hp.outlet_temp_entity);
    const outletEl = this.shadowRoot.querySelector('#temp-outlet');
    if (outletEl && outletTemp !== null) {
      outletEl.textContent = `${outletTemp.toFixed(1)}°${this._config.temperature.unit}`;
    }

    // Update inlet temperature
    const inletTemp = this.getEntityValue(hp.inlet_temp_entity);
    const inletEl = this.shadowRoot.querySelector('#temp-inlet');
    if (inletEl && inletTemp !== null) {
      inletEl.textContent = `${inletTemp.toFixed(1)}°${this._config.temperature.unit}`;
    }

    // Update buffer tank temperatures if configured
    if (this._config.buffer_tank) {
      const supplyTemp = this.getEntityValue(this._config.buffer_tank.supply_temp_entity);
      const supplyEl = this.shadowRoot.querySelector('#temp-buffer-supply');
      if (supplyEl && supplyTemp !== null) {
        supplyEl.textContent = `${supplyTemp.toFixed(1)}°${this._config.temperature.unit}`;
      }

      const returnTemp = this.getEntityValue(this._config.buffer_tank.return_temp_entity);
      const returnEl = this.shadowRoot.querySelector('#temp-buffer-return');
      if (returnEl && returnTemp !== null) {
        returnEl.textContent = `${returnTemp.toFixed(1)}°${this._config.temperature.unit}`;
      }
    }
  }

  getTemperatureColor(temp) {
    if (temp === null) return this._config.temperature.neutral_color;
    
    // Use threshold to determine color based on absolute temperature
    // For heating: temps above threshold are hot (red)
    // For cooling: temps below negative threshold are cold (blue)
    const threshold = this._config.temperature.delta_threshold;
    const hotColor = this._config.temperature.hot_color;
    const coldColor = this._config.temperature.cold_color;
    const neutralColor = this._config.temperature.neutral_color;

    // Compare against typical room temperature (20°C)
    const roomTemp = 20;
    const tempDiff = temp - roomTemp;

    if (tempDiff > threshold) {
      return hotColor;
    } else if (tempDiff < -threshold) {
      return coldColor;
    } else {
      return neutralColor;
    }
  }

  updateColors() {
    const hp = this._config.heat_pump;
    const visual = this._config.heat_pump_visual;
    
    // Determine heat pump mode
    let hpColor = visual.off_color;
    const power = this.getEntityValue(hp.power_entity);
    
    if (power && power > 0.1) {
      // Simplified: if power is on, assume heating mode
      // In a full implementation, you'd check mode_entity
      hpColor = visual.heating_color;
    }

    // Update heat pump color
    const hpRect = this.shadowRoot.querySelector('#hp-unit');
    if (hpRect) {
      hpRect.setAttribute('fill', hpColor);
    }

    // Update pipe colors based on temperatures
    const outletTemp = this.getEntityValue(hp.outlet_temp_entity);
    const inletTemp = this.getEntityValue(hp.inlet_temp_entity);
    
    if (outletTemp !== null) {
      const color = this.getTemperatureColor(outletTemp);
      const outletPipe = this.shadowRoot.querySelector('#pipe-outlet');
      if (outletPipe) {
        outletPipe.setAttribute('stroke', color);
      }
    }

    if (inletTemp !== null) {
      const color = this.getTemperatureColor(inletTemp);
      const inletPipe = this.shadowRoot.querySelector('#pipe-inlet');
      if (inletPipe) {
        inletPipe.setAttribute('stroke', color);
      }
    }
  }

  updateAnimation() {
    if (!this._config.animation.enabled) return;

    const flow = this.getEntityValue(this._config.heat_pump.flow_rate_entity);
    
    if (flow && flow > this._config.animation.idle_threshold) {
      // Calculate animation speed based on flow rate
      const maxFlow = this._config.animation.max_flow_rate_value;
      const minSpeed = this._config.animation.min_flow_rate;
      const maxSpeed = this._config.animation.max_flow_rate;
      
      // Prevent division by zero
      if (maxFlow <= 0) {
        this.stopAnimation();
        return;
      }
      
      const speed = minSpeed + ((maxSpeed - minSpeed) * (flow / maxFlow));
      
      // Start animation if not already running
      if (!this._animationFrame) {
        this.startAnimation(speed);
      }
    } else {
      // Stop animation
      this.stopAnimation();
    }
  }

  startAnimation(speed) {
    const animate = () => {
      // Update dot positions
      const dots = this.shadowRoot.querySelectorAll('.flow-dot');
      dots.forEach((dot, index) => {
        const offset = parseFloat(dot.getAttribute('data-offset') || 0);
        const newOffset = (offset + speed) % 100;
        dot.setAttribute('data-offset', newOffset);
        
        // Update position along path
        // This is a simplified animation - full implementation would use path calculations
        const x = 150 + (newOffset * 2);
        const y = 250;
        dot.setAttribute('cx', x);
        dot.setAttribute('cy', y);
      });

      this._animationFrame = requestAnimationFrame(animate);
    };

    this._animationFrame = requestAnimationFrame(animate);
  }

  stopAnimation() {
    if (this._animationFrame) {
      cancelAnimationFrame(this._animationFrame);
      this._animationFrame = null;
    }
  }

  render() {
    const hp = this._config.heat_pump;
    const displayName = hp.display_name || 'Heat Pump';

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          padding: 16px;
        }
        .card {
          background: var(--ha-card-background, var(--card-background-color, white));
          border-radius: var(--ha-card-border-radius, 12px);
          box-shadow: var(--ha-card-box-shadow, 0 2px 8px rgba(0,0,0,0.1));
          padding: 16px;
        }
        .card-header {
          font-size: 24px;
          font-weight: bold;
          margin-bottom: 16px;
          color: var(--primary-text-color);
        }
        .visualization {
          width: 100%;
          min-height: 400px;
        }
        .metrics {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
          gap: 12px;
          margin-top: 16px;
        }
        .metric {
          background: var(--secondary-background-color);
          border-radius: 8px;
          padding: 12px;
          text-align: center;
        }
        .metric-label {
          font-size: 12px;
          color: var(--secondary-text-color);
          margin-bottom: 4px;
        }
        .metric-value {
          font-size: 18px;
          font-weight: bold;
          color: var(--primary-text-color);
          font-family: ${this._config.text_style.font_family};
        }
        .flow-dot {
          fill: ${this._config.animation.dot_color};
          opacity: ${this._config.animation.dot_opacity};
        }
        .temp-indicator {
          font-family: ${this._config.text_style.font_family};
          font-size: ${this._config.text_style.font_size}px;
          font-weight: ${this._config.text_style.font_weight};
          fill: var(--primary-text-color);
        }
        .clickable {
          cursor: pointer;
        }
        .clickable:hover {
          opacity: 0.8;
        }
      </style>
      
      <ha-card class="card">
        <div class="card-header">${this._config.title}</div>
        
        <svg class="visualization" viewBox="0 0 600 400" xmlns="http://www.w3.org/2000/svg">
          <!-- Heat Pump Unit -->
          <g id="heat-pump">
            <rect id="hp-unit" x="50" y="180" width="100" height="80" 
                  fill="${this._config.heat_pump_visual.off_color}" 
                  stroke="var(--primary-text-color)" stroke-width="2" rx="5"/>
            <text x="100" y="210" text-anchor="middle" class="temp-indicator">${displayName}</text>
            
            <!-- Fan animation placeholder -->
            ${this._config.heat_pump_visual.animate_fan ? `
              <circle cx="100" cy="240" r="15" fill="none" 
                      stroke="var(--primary-text-color)" stroke-width="1.5"/>
              <line x1="100" y1="225" x2="100" y2="255" 
                    stroke="var(--primary-text-color)" stroke-width="1.5"/>
              <line x1="85" y1="240" x2="115" y2="240" 
                    stroke="var(--primary-text-color)" stroke-width="1.5"/>
            ` : ''}
          </g>

          ${this._config.buffer_tank ? `
            <!-- WITH BUFFER TANK LAYOUT -->
            <!-- Outlet pipe (hot) to buffer -->
            <g id="outlet-section">
              <path id="pipe-outlet" d="M 150 200 L 250 200" 
                    stroke="${this._config.temperature.hot_color}" 
                    stroke-width="8" fill="none"/>
              <circle class="flow-dot" cx="150" cy="200" r="${this._config.animation.dot_size}" data-offset="0"/>
              <circle class="flow-dot" cx="180" cy="200" r="${this._config.animation.dot_size}" data-offset="30"/>
              <circle class="flow-dot" cx="210" cy="200" r="${this._config.animation.dot_size}" data-offset="60"/>
              <text id="temp-outlet" x="200" y="190" text-anchor="middle" class="temp-indicator">--°C</text>
            </g>

            <!-- Buffer Tank -->
            <g id="buffer-tank">
              <rect x="250" y="150" width="80" height="100" 
                    fill="${this._config.temperature.neutral_color}" 
                    stroke="var(--primary-text-color)" stroke-width="2" rx="5"/>
              <text x="290" y="175" text-anchor="middle" class="temp-indicator">
                ${this._config.buffer_tank.name || 'BUFFER'}
              </text>
              <text id="temp-buffer-supply" x="290" y="195" text-anchor="middle" class="temp-indicator">--°C</text>
              <text id="temp-buffer-return" x="290" y="235" text-anchor="middle" class="temp-indicator">--°C</text>
            </g>

            <!-- HVAC supply line from buffer -->
            <path d="M 330 180 L 450 180" 
                  stroke="${this._config.temperature.hot_color}" 
                  stroke-width="6" fill="none"/>
            
            <!-- HVAC return line to buffer -->
            <path d="M 450 220 L 330 220" 
                  stroke="${this._config.temperature.cold_color}" 
                  stroke-width="6" fill="none"/>
            
            <!-- House/HVAC Load -->
            <g id="hvac-load">
              <rect x="450" y="160" width="100" height="80" 
                    fill="var(--secondary-background-color)" 
                    stroke="var(--primary-text-color)" stroke-width="2" rx="5"/>
              <text x="500" y="195" text-anchor="middle" class="temp-indicator">HEATING</text>
              <text x="500" y="215" text-anchor="middle" class="temp-indicator">LOAD</text>
              <text x="500" y="230" text-anchor="middle" class="temp-indicator" style="font-size: 9px;">(Radiators/Floor)</text>
            </g>

            <!-- Return pipe (cold) from buffer to HP -->
            <g id="inlet-section">
              <path id="pipe-inlet" d="M 250 240 L 150 240" 
                    stroke="${this._config.temperature.cold_color}" 
                    stroke-width="8" fill="none"/>
              <circle class="flow-dot" cx="250" cy="240" r="${this._config.animation.dot_size}" data-offset="0"/>
              <circle class="flow-dot" cx="220" cy="240" r="${this._config.animation.dot_size}" data-offset="30"/>
              <circle class="flow-dot" cx="190" cy="240" r="${this._config.animation.dot_size}" data-offset="60"/>
              <text id="temp-inlet" x="200" y="260" text-anchor="middle" class="temp-indicator">--°C</text>
            </g>
          ` : `
            <!-- SIMPLE LAYOUT (No Buffer Tank) - Direct heating circuit -->
            <!-- Outlet pipe (hot) from HP -->
            <g id="outlet-section">
              <path id="pipe-outlet" d="M 150 200 L 300 200" 
                    stroke="${this._config.temperature.hot_color}" 
                    stroke-width="8" fill="none"/>
              <circle class="flow-dot" cx="170" cy="200" r="${this._config.animation.dot_size}" data-offset="0"/>
              <circle class="flow-dot" cx="210" cy="200" r="${this._config.animation.dot_size}" data-offset="25"/>
              <circle class="flow-dot" cx="250" cy="200" r="${this._config.animation.dot_size}" data-offset="50"/>
              <circle class="flow-dot" cx="280" cy="200" r="${this._config.animation.dot_size}" data-offset="75"/>
              <text id="temp-outlet" x="225" y="190" text-anchor="middle" class="temp-indicator">--°C</text>
            </g>

            <!-- Vertical pipe up to heating load -->
            <path d="M 300 200 L 300 120" 
                  stroke="${this._config.temperature.hot_color}" 
                  stroke-width="8" fill="none"/>
            
            <!-- Horizontal pipe to heating load -->
            <path d="M 300 120 L 450 120" 
                  stroke="${this._config.temperature.hot_color}" 
                  stroke-width="8" fill="none"/>

            <!-- House/Heating Load -->
            <g id="hvac-load">
              <rect x="450" y="80" width="100" height="100" 
                    fill="var(--secondary-background-color)" 
                    stroke="var(--primary-text-color)" stroke-width="2" rx="5"/>
              <text x="500" y="115" text-anchor="middle" class="temp-indicator">HEATING</text>
              <text x="500" y="135" text-anchor="middle" class="temp-indicator">LOAD</text>
              <text x="500" y="155" text-anchor="middle" class="temp-indicator" style="font-size: 9px;">(Radiators/</text>
              <text x="500" y="168" text-anchor="middle" class="temp-indicator" style="font-size: 9px;">Floor Heating)</text>
            </g>

            <!-- Horizontal return pipe from heating load -->
            <path d="M 450 160 L 300 160" 
                  stroke="${this._config.temperature.cold_color}" 
                  stroke-width="8" fill="none"/>
            
            <!-- Vertical pipe down from heating load -->
            <path d="M 300 160 L 300 240" 
                  stroke="${this._config.temperature.cold_color}" 
                  stroke-width="8" fill="none"/>

            <!-- Return pipe (cold) back to HP -->
            <g id="inlet-section">
              <path id="pipe-inlet" d="M 300 240 L 150 240" 
                    stroke="${this._config.temperature.cold_color}" 
                    stroke-width="8" fill="none"/>
              <circle class="flow-dot" cx="280" cy="240" r="${this._config.animation.dot_size}" data-offset="0"/>
              <circle class="flow-dot" cx="250" cy="240" r="${this._config.animation.dot_size}" data-offset="25"/>
              <circle class="flow-dot" cx="210" cy="240" r="${this._config.animation.dot_size}" data-offset="50"/>
              <circle class="flow-dot" cx="170" cy="240" r="${this._config.animation.dot_size}" data-offset="75"/>
              <text id="temp-inlet" x="225" y="260" text-anchor="middle" class="temp-indicator">--°C</text>
            </g>
          `}
        </svg>

        ${this._config.heat_pump_visual.show_metrics ? `
        <div class="metrics">
          <div class="metric">
            <div class="metric-label">Power Input</div>
            <div class="metric-value" id="power-value">-- kW</div>
          </div>
          <div class="metric">
            <div class="metric-label">Thermal Output</div>
            <div class="metric-value" id="thermal-value">-- kW</div>
          </div>
          <div class="metric">
            <div class="metric-label">COP</div>
            <div class="metric-value" id="cop-value">--</div>
          </div>
          <div class="metric">
            <div class="metric-label">Flow Rate</div>
            <div class="metric-value" id="flow-value">-- m³/h</div>
          </div>
        </div>
        ` : ''}
      </ha-card>
    `;

    // Initial update if hass is available
    if (this._hass) {
      this.updateCard();
    }
  }

  disconnectedCallback() {
    this.stopAnimation();
  }

  static getStubConfig() {
    return {
      title: 'Heat Pump Flow',
      heat_pump: {
        power_entity: 'sensor.neore_actual_power_usage',
        thermal_entity: 'sensor.neore_supplied_power',
        cop_entity: 'sensor.neore_cop',
        outlet_temp_entity: 'sensor.neore_output_temperature',
        inlet_temp_entity: 'sensor.neore_input_temperature',
        flow_rate_entity: 'sensor.neore_water_flow',
        display_name: 'Neore Heat Pump'
      }
    };
  }
}

customElements.define('heat-pump-flow-card', HeatPumpFlowCard);

// Register the card with Home Assistant
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'heat-pump-flow-card',
  name: 'Heat Pump Flow Card',
  description: 'Visualizes heat pump water flow with animated pipes and temperature gradients',
  preview: true,
  documentationURL: 'https://github.com/vbrhino/hass-neore'
});

console.info(
  '%c  HEAT-PUMP-FLOW-CARD  \n%c  Version 1.0.0        ',
  'color: orange; font-weight: bold; background: black',
  'color: white; font-weight: bold; background: dimgray'
);
