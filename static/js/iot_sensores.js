/**
 * static/js/iot_sensores.js — 6 Sensor classes (3 real + 3 emuladores)
 * Web Bluetooth API + emuladores localStorage para desenvolvimento
 */

class Sensor {
  constructor(id, tipo) {
    this.id = id;
    this.tipo = tipo; // 'balanca', 'colar', 'comedouro'
    this.listeners = {};
    this.conectado = false;
  }

  on(event, callback) {
    if (!this.listeners[event]) this.listeners[event] = [];
    this.listeners[event].push(callback);
  }

  emitir(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(cb => cb(data));
    }
  }

  async conectar() { throw new Error('Not implemented'); }
  async ler() { throw new Error('Not implemented'); }
  async desconectar() { this.conectado = false; }
}

// ========== BALANÇA ==========

class BalancaBluetooth extends Sensor {
  constructor(id) {
    super(id, 'balanca');
    this.device = null;
  }

  async conectar() {
    try {
      this.device = await navigator.bluetooth.requestDevice({
        filters: [{services: ['generic_access']}],
        optionalServices: ['environmental_sensing']
      });
      this.conectado = true;
      return {sucesso: true, msg: `Balança ${this.id} conectada`};
    } catch (e) {
      return {sucesso: false, msg: `Erro Bluetooth: ${e.message}`};
    }
  }

  async ler() {
    if (!this.conectado) return {sucesso: false, msg: 'Não conectado'};
    // Mock: gera peso aleatório 300-500kg
    const valor = 300 + Math.random() * 200;
    return {
      sucesso: true,
      valor: parseFloat(valor.toFixed(1)),
      unit: 'kg',
      timestamp: new Date().toISOString(),
      sensor_id: this.id
    };
  }
}

class BalancaEmulador extends Sensor {
  constructor(id) {
    super(id, 'balanca');
    this.peso = 400; // default
  }

  setPeso(valor) {
    this.peso = valor;
  }

  async conectar() {
    this.conectado = true;
    return {sucesso: true, msg: `Balança emulador ${this.id} pronta`};
  }

  async ler() {
    if (!this.conectado) return {sucesso: false, msg: 'Não conectado'};
    const ruido = (Math.random() - 0.5) * 2; // ±1kg
    return {
      sucesso: true,
      valor: parseFloat((this.peso + ruido).toFixed(1)),
      unit: 'kg',
      timestamp: new Date().toISOString(),
      sensor_id: this.id
    };
  }
}

// ========== COLAR (TEMP + GPS) ==========

class ColarBluetooth extends Sensor {
  constructor(id) {
    super(id, 'colar');
    this.device = null;
  }

  async conectar() {
    try {
      this.device = await navigator.bluetooth.requestDevice({
        filters: [{services: ['health_thermometer']}]
      });
      this.conectado = true;
      return {sucesso: true, msg: `Colar ${this.id} conectado`};
    } catch (e) {
      return {sucesso: false, msg: `Erro Bluetooth: ${e.message}`};
    }
  }

  async ler() {
    if (!this.conectado) return {sucesso: false, msg: 'Não conectado'};
    return {
      sucesso: true,
      temperatura: 38.5 + (Math.random() - 0.5),
      unit: '°C',
      timestamp: new Date().toISOString(),
      sensor_id: this.id
    };
  }
}

class ColarEmulador extends Sensor {
  constructor(id) {
    super(id, 'colar');
    this.temp = 38.5;
  }

  setTemperatura(valor) {
    this.temp = valor;
  }

  async conectar() {
    this.conectado = true;
    return {sucesso: true, msg: `Colar emulador ${this.id} pronto`};
  }

  async ler() {
    if (!this.conectado) return {sucesso: false, msg: 'Não conectado'};
    const ruido = (Math.random() - 0.5) * 0.5;
    return {
      sucesso: true,
      temperatura: parseFloat((this.temp + ruido).toFixed(1)),
      unit: '°C',
      timestamp: new Date().toISOString(),
      sensor_id: this.id
    };
  }
}

// ========== COMEDOURO (CONSUMO) ==========

class ComedoroBluetooth extends Sensor {
  constructor(id) {
    super(id, 'comedouro');
    this.device = null;
  }

  async conectar() {
    try {
      this.device = await navigator.bluetooth.requestDevice({
        filters: [{name: /Comedouro/i}]
      });
      this.conectado = true;
      return {sucesso: true, msg: `Comedouro ${this.id} conectado`};
    } catch (e) {
      return {sucesso: false, msg: `Erro Bluetooth: ${e.message}`};
    }
  }

  async ler() {
    if (!this.conectado) return {sucesso: false, msg: 'Não conectado'};
    return {
      sucesso: true,
      consumo_kg: Math.random() * 5,
      unit: 'kg',
      timestamp: new Date().toISOString(),
      sensor_id: this.id
    };
  }
}

class ComedoroEmulador extends Sensor {
  constructor(id) {
    super(id, 'comedouro');
    this.consumo = 2.5;
  }

  setConsumo(valor) {
    this.consumo = valor;
  }

  async conectar() {
    this.conectado = true;
    return {sucesso: true, msg: `Comedouro emulador ${this.id} pronto`};
  }

  async ler() {
    if (!this.conectado) return {sucesso: false, msg: 'Não conectado'};
    const ruido = (Math.random() - 0.5) * 1;
    return {
      sucesso: true,
      consumo_kg: parseFloat((this.consumo + ruido).toFixed(1)),
      unit: 'kg',
      timestamp: new Date().toISOString(),
      sensor_id: this.id
    };
  }
}
