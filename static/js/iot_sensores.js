/*
 * Adaptadores de sensores físicos/emulados existentes.
 * Os adaptadores manuais ao final normalizam dispositivos sem protocolo conhecido.
 */

class Sensor {
  constructor(id, tipo) { this.id = id; this.tipo = tipo; this.listeners = {}; this.conectado = false; }
  on(event, callback) { (this.listeners[event] ||= []).push(callback); }
  emitir(event, data) { (this.listeners[event] || []).forEach(cb => cb(data)); }
  async conectar() { throw new Error('Not implemented'); }
  async ler() { throw new Error('Not implemented'); }
  async desconectar() { this.conectado = false; }
}

class BalancaBluetooth extends Sensor {
  constructor(id) { super(id, 'balanca'); this.device = null; }
  async conectar() {
    if (!navigator.bluetooth) return {sucesso: false, msg: 'Bluetooth não suportado neste navegador'};
    try { this.device = await navigator.bluetooth.requestDevice({filters: [{services: ['generic_access']}], optionalServices: ['environmental_sensing']}); this.conectado = true; return {sucesso: true, msg: `Balança ${this.id} conectada`}; }
    catch (e) { return {sucesso: false, msg: `Erro Bluetooth: ${e.message}`}; }
  }
  async ler() { return this.conectado ? {sucesso: true, valor: 300 + Math.random() * 200, unit: 'kg', timestamp: new Date().toISOString(), sensor_id: this.id} : {sucesso: false, msg: 'Não conectado'}; }
}
class BalancaEmulador extends Sensor {
  constructor(id) { super(id, 'balanca'); this.peso = 400; }
  setPeso(valor) { this.peso = valor; }
  async conectar() { this.conectado = true; return {sucesso: true, msg: `Balança emulador ${this.id} pronta`}; }
  async ler() { return this.conectado ? {sucesso: true, valor: parseFloat((this.peso + (Math.random() - .5) * 2).toFixed(1)), unit: 'kg', timestamp: new Date().toISOString(), sensor_id: this.id} : {sucesso: false, msg: 'Não conectado'}; }
}
class ColarBluetooth extends Sensor {
  constructor(id) { super(id, 'colar'); }
  async conectar() { if (!navigator.bluetooth) return {sucesso: false, msg: 'Bluetooth não suportado neste navegador'}; try { await navigator.bluetooth.requestDevice({filters: [{services: ['health_thermometer']}]}); this.conectado = true; return {sucesso: true, msg: `Colar ${this.id} conectado`}; } catch (e) { return {sucesso: false, msg: `Erro Bluetooth: ${e.message}`}; } }
  async ler() { return this.conectado ? {sucesso: true, temperatura: 38.5, unit: '°C', timestamp: new Date().toISOString(), sensor_id: this.id} : {sucesso: false, msg: 'Não conectado'}; }
}
class ColarEmulador extends Sensor {
  constructor(id) { super(id, 'colar'); this.temp = 38.5; }
  setTemperatura(valor) { this.temp = valor; }
  async conectar() { this.conectado = true; return {sucesso: true, msg: `Colar emulador ${this.id} pronto`}; }
  async ler() { return this.conectado ? {sucesso: true, temperatura: parseFloat((this.temp + (Math.random() - .5) * .5).toFixed(1)), unit: '°C', timestamp: new Date().toISOString(), sensor_id: this.id} : {sucesso: false, msg: 'Não conectado'}; }
}
class ComedoroBluetooth extends Sensor {
  constructor(id) { super(id, 'comedouro'); }
  async conectar() { if (!navigator.bluetooth) return {sucesso: false, msg: 'Bluetooth não suportado neste navegador'}; try { await navigator.bluetooth.requestDevice({filters: [{name: /Comedouro/i}]}); this.conectado = true; return {sucesso: true, msg: `Comedouro ${this.id} conectado`}; } catch (e) { return {sucesso: false, msg: `Erro Bluetooth: ${e.message}`}; } }
  async ler() { return this.conectado ? {sucesso: true, consumo_kg: 2.5, unit: 'kg', timestamp: new Date().toISOString(), sensor_id: this.id} : {sucesso: false, msg: 'Não conectado'}; }
}
class ComedoroEmulador extends Sensor {
  constructor(id) { super(id, 'comedouro'); this.consumo = 2.5; }
  setConsumo(valor) { this.consumo = valor; }
  async conectar() { this.conectado = true; return {sucesso: true, msg: `Comedouro emulador ${this.id} pronto`}; }
  async ler() { return this.conectado ? {sucesso: true, consumo_kg: parseFloat((this.consumo + (Math.random() - .5)).toFixed(1)), unit: 'kg', timestamp: new Date().toISOString(), sensor_id: this.id} : {sucesso: false, msg: 'Não conectado'}; }
}

class RfidManual { constructor(id) { this.id = id; } async ler(tag_id) { return {sucesso: Boolean(tag_id), tag_id, sensor_id: this.id, timestamp: new Date().toISOString()}; } }
class AguaManual { constructor(id) { this.id = id; } async ler(valor, unidade = 'L', lote_id = '') { return {sucesso: Number(valor) >= 0, valor: Number(valor), unidade, lote_id, sensor_id: this.id, timestamp: new Date().toISOString()}; } }
class CochoManual { constructor(id) { this.id = id; } async ler(consumo_kg, unidade = 'kg', lote_id = '') { return {sucesso: Number(consumo_kg) >= 0, consumo_kg: Number(consumo_kg), unidade, lote_id, sensor_id: this.id, timestamp: new Date().toISOString()}; } }
