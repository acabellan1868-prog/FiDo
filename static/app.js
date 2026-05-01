/**
 * FiDo — Componente Alpine.js principal.
 * Gestiona toda la lógica del frontend SPA.
 */
function fidoApp() {
    return {
        // Navegación
        pestana: 'panel',
        drawerAbierto: false,

        // Estado del panel
        resumen: { ingresos: 0, gastos: 0, balance: 0, total_movimientos: 0 },
        datosPorCategoria: [],
        datosPorMes: [],
        graficaCategoria: null,
        graficaMes: null,
        filtroPanelMes: '',
        filtroPanelCuenta: '',

        // Estado de movimientos
        movimientos: [],
        totalMovimientos: 0,
        filtros: { mes: '', cuenta_id: '', categoria_id: '', tipo: '', buscar: '', estado: '', offset: 0 },
        sumaMovimientos: 0,
        editandoMovimiento: null,
        mostrarFormularioMovimiento: false,
        nuevoMovimiento: { fecha: '', importe: '', descripcion: '', cuenta_id: '', categoria_id: '', origen: 'web', notas: '', estado: 'ok' },

        // Estado de importación
        resultadoImportacion: null,
        importando: false,
        importarCuentaId: '',
        importarBanco: 'santander',

        // Datos maestros
        categorias: [],
        categoriasPlanas: [],
        reglas: [],
        miembros: [],
        cuentas: [],
        mapeoTarjetas: [],
        vinculaciones: [],

        // Formularios
        nuevaRegla: { patron: '', categoria_id: '', prioridad: 0 },
        nuevoMiembro: { nombre: '', telegram_chat_id: '' },
        nuevaCuenta: { nombre: '', banco: '', miembro_id: '', es_compartida: false },
        editandoCuenta: null,
        nuevoMapeo: { ultimos4: '', cuenta_id: '', etiqueta: '' },
        nuevaVinculacion: { cuenta_principal_id: '', cuenta_vinculada_id: '', patron_principal: 'Recarga', patron_vinculada: 'Recargas: Pago de%', tolerancia_dias: 1 },

        // Crypto
        portafolioCrypto: [],
        grafica24: null,
        cargandoCrypto: true,
        errorCrypto: '',

        // Mensajes
        mensaje: '',
        tipoMensaje: 'ok',

        async init() {
            // Cargar datos maestros
            await this.cargarDatosMaestros();
            // Fecha por defecto: mes actual
            const hoy = new Date();
            this.filtroPanelMes = `${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, '0')}`;
            this.filtros.mes = this.filtroPanelMes;
            this.nuevoMovimiento.fecha = hoy.toISOString().split('T')[0];
            // Cargar panel
            await this.cargarPanel();
        },

        async cargarDatosMaestros() {
            try {
                [this.categorias, this.categoriasPlanas, this.cuentas, this.miembros] = await Promise.all([
                    API.obtener('/categorias'),
                    API.obtener('/categorias/planas'),
                    API.obtener('/cuentas'),
                    API.obtener('/miembros'),
                ]);
            } catch (e) {
                this.mostrarError('Error cargando datos: ' + e.message);
            }
        },

        // ---- PANEL ----
        async cargarPanel() {
            try {
                const params = new URLSearchParams();
                if (this.filtroPanelMes) params.set('mes', this.filtroPanelMes);
                if (this.filtroPanelCuenta) params.set('cuenta_id', this.filtroPanelCuenta);
                const qs = params.toString() ? '?' + params.toString() : '';

                [this.resumen, this.datosPorCategoria, this.datosPorMes] = await Promise.all([
                    API.obtener('/panel/resumen' + qs),
                    API.obtener('/panel/por-categoria' + qs),
                    API.obtener('/panel/por-mes' + (this.filtroPanelCuenta ? '?cuenta_id=' + this.filtroPanelCuenta : '')),
                ]);

                this.$nextTick(() => {
                    this.renderizarGraficaCategoria();
                    this.renderizarGraficaMes();
                });
            } catch (e) {
                this.mostrarError('Error cargando panel: ' + e.message);
            }
        },

        renderizarGraficaCategoria() {
            const el = document.getElementById('graficaCategoria');
            if (!el || !this.datosPorCategoria.length) return;
            if (this.graficaCategoria) this.graficaCategoria.destroy();

            const colores = [
                '#3B82F6', '#EF4444', '#10B981', '#F59E0B', '#8B5CF6',
                '#EC4899', '#06B6D4', '#84CC16', '#F97316', '#6366F1',
                '#14B8A6', '#E11D48', '#A855F7',
            ];

            this.graficaCategoria = new ApexCharts(el, {
                chart: { type: 'donut', height: 300 },
                series: this.datosPorCategoria.map(c => Math.round(c.total * 100) / 100),
                labels: this.datosPorCategoria.map(c => (c.icono || '') + ' ' + c.nombre),
                colors: colores.slice(0, this.datosPorCategoria.length),
                legend: { position: 'right', fontSize: '11px' },
                dataLabels: { enabled: false },
            });
            this.graficaCategoria.render();
        },

        renderizarGraficaMes() {
            const el = document.getElementById('graficaMes');
            if (!el || !this.datosPorMes.length) return;
            if (this.graficaMes) this.graficaMes.destroy();

            this.graficaMes = new ApexCharts(el, {
                chart: { type: 'bar', height: 300 },
                series: [
                    { name: 'Ingresos', data: this.datosPorMes.map(m => m.ingresos) },
                    { name: 'Gastos', data: this.datosPorMes.map(m => m.gastos) },
                ],
                xaxis: { categories: this.datosPorMes.map(m => m.mes) },
                colors: ['#10B981', '#EF4444'],
                legend: { position: 'top' },
                dataLabels: { enabled: false },
            });
            this.graficaMes.render();
        },

        // ---- MOVIMIENTOS ----
        async cargarMovimientos() {
            try {
                const params = new URLSearchParams();
                if (this.filtros.mes) params.set('mes', this.filtros.mes);
                if (this.filtros.cuenta_id) params.set('cuenta_id', this.filtros.cuenta_id);
                if (this.filtros.categoria_id) params.set('categoria_id', this.filtros.categoria_id);
                if (this.filtros.tipo) params.set('tipo', this.filtros.tipo);
                if (this.filtros.buscar) params.set('buscar', this.filtros.buscar);
                if (this.filtros.estado) params.set('estado', this.filtros.estado);
                params.set('offset', this.filtros.offset);
                params.set('limite', '50');
                const qs = '?' + params.toString();

                [this.movimientos, { total: this.totalMovimientos, suma: this.sumaMovimientos }] = await Promise.all([
                    API.obtener('/movimientos' + qs),
                    API.obtener('/movimientos/total' + qs),
                ]);
            } catch (e) {
                this.mostrarError('Error cargando movimientos: ' + e.message);
            }
        },

        async guardarMovimiento() {
            try {
                const datos = { ...this.nuevoMovimiento };
                datos.importe = parseFloat(datos.importe);
                datos.cuenta_id = parseInt(datos.cuenta_id);
                if (datos.categoria_id) datos.categoria_id = parseInt(datos.categoria_id);
                else datos.categoria_id = null;

                if (this.editandoMovimiento) {
                    await API.actualizar('/movimientos/' + this.editandoMovimiento.id, datos);
                    this.mostrarOk('Movimiento actualizado');
                } else {
                    await API.crear('/movimientos', datos);
                    this.mostrarOk('Movimiento creado');
                }
                this.cancelarEdicionMovimiento();
                await this.cargarMovimientos();
            } catch (e) {
                this.mostrarError('Error: ' + e.message);
            }
        },

        editarMovimiento(mov) {
            this.editandoMovimiento = mov;
            this.nuevoMovimiento = {
                fecha: mov.fecha,
                importe: mov.importe,
                descripcion: mov.descripcion,
                cuenta_id: mov.cuenta_id,
                categoria_id: mov.categoria_id || '',
                origen: mov.origen,
                notas: mov.notas || '',
                estado: mov.estado || 'ok',
            };
            this.mostrarFormularioMovimiento = true;
        },

        cancelarEdicionMovimiento() {
            this.editandoMovimiento = null;
            this.mostrarFormularioMovimiento = false;
            const hoy = new Date().toISOString().split('T')[0];
            this.nuevoMovimiento = { fecha: hoy, importe: '', descripcion: '', cuenta_id: '', categoria_id: '', origen: 'web', notas: '', estado: 'ok' };
        },

        async marcarEstado(id, nuevoEstado) {
            try {
                await API.actualizar(`/movimientos/${id}/estado?nuevo_estado=${nuevoEstado}`, {});
                await this.cargarMovimientos();
            } catch (e) {
                this.mostrarError('Error cambiando estado: ' + e.message);
            }
        },

        async borrarMovimiento(id) {
            if (!confirm('¿Seguro que quieres borrar este movimiento?')) return;
            try {
                await API.borrar('/movimientos/' + id);
                this.mostrarOk('Movimiento borrado');
                await this.cargarMovimientos();
            } catch (e) {
                this.mostrarError('Error: ' + e.message);
            }
        },

        // ---- IMPORTAR ----
        async importarCSV() {
            const ficheroInput = document.getElementById('ficheroCSV');
            const cuentaId = this.importarCuentaId;
            const banco = this.importarBanco;

            if (!ficheroInput.files.length || !cuentaId) {
                this.mostrarError('Selecciona un fichero y una cuenta');
                return;
            }

            this.importando = true;
            this.resultadoImportacion = null;
            try {
                this.resultadoImportacion = await API.subirCSV(ficheroInput.files[0], cuentaId, banco);
                this.mostrarOk(`Importados: ${this.resultadoImportacion.importados}, Duplicados: ${this.resultadoImportacion.duplicados}`);
            } catch (e) {
                this.mostrarError('Error importando: ' + e.message);
            } finally {
                this.importando = false;
            }
        },

        async recategorizar() {
            try {
                const resp = await API.crear('/movimientos/recategorizar', {});
                this.mostrarOk(`Recategorizados: ${resp.recategorizados} de ${resp.total_sin_categoria} sin categoría`);
                await this.cargarPanel();
            } catch (e) {
                this.mostrarError('Error: ' + e.message);
            }
        },

        // ---- CATEGORÍAS ----
        async cargarCategorias() {
            this.categorias = await API.obtener('/categorias');
            this.categoriasPlanas = await API.obtener('/categorias/planas');
        },

        async crearSubcategoria(padreId) {
            const nombre = prompt('Nombre de la subcategoría:');
            if (!nombre) return;
            try {
                await API.crear('/categorias', { nombre, padre_id: padreId, orden: 0 });
                this.mostrarOk('Subcategoría creada');
                await this.cargarCategorias();
            } catch (e) {
                this.mostrarError('Error: ' + e.message);
            }
        },

        async crearCategoriaPadre() {
            const nombre = prompt('Nombre de la categoría:');
            if (!nombre) return;
            const icono = prompt('Emoji (opcional):', '📁');
            try {
                await API.crear('/categorias', { nombre, icono: icono || '📁', orden: 0 });
                this.mostrarOk('Categoría creada');
                await this.cargarCategorias();
            } catch (e) {
                this.mostrarError('Error: ' + e.message);
            }
        },

        async borrarCategoria(id) {
            if (!confirm('¿Seguro? Se borrarán también las subcategorías')) return;
            try {
                await API.borrar('/categorias/' + id);
                this.mostrarOk('Categoría borrada');
                await this.cargarCategorias();
            } catch (e) {
                this.mostrarError('Error: ' + e.message);
            }
        },

        // ---- REGLAS ----
        async cargarReglas() {
            this.reglas = await API.obtener('/reglas');
        },

        async guardarRegla() {
            try {
                await API.crear('/reglas', {
                    patron: this.nuevaRegla.patron,
                    categoria_id: parseInt(this.nuevaRegla.categoria_id),
                    prioridad: parseInt(this.nuevaRegla.prioridad) || 0,
                });
                this.nuevaRegla = { patron: '', categoria_id: '', prioridad: 0 };
                this.mostrarOk('Regla creada');
                await this.cargarReglas();
            } catch (e) {
                this.mostrarError('Error: ' + e.message);
            }
        },

        async borrarRegla(id) {
            if (!confirm('¿Borrar esta regla?')) return;
            try {
                await API.borrar('/reglas/' + id);
                this.mostrarOk('Regla borrada');
                await this.cargarReglas();
            } catch (e) {
                this.mostrarError('Error: ' + e.message);
            }
        },

        // ---- AJUSTES ----
        async cargarAjustes() {
            [this.miembros, this.cuentas, this.mapeoTarjetas] = await Promise.all([
                API.obtener('/miembros'),
                API.obtener('/cuentas'),
                API.obtener('/mapeo-tarjetas'),
            ]);
            try {
                this.vinculaciones = await API.obtener('/transferencias/vinculaciones');
            } catch (_) {
                this.vinculaciones = [];
            }
        },

        async guardarMiembro() {
            try {
                await API.crear('/miembros', this.nuevoMiembro);
                this.nuevoMiembro = { nombre: '', telegram_chat_id: '' };
                this.mostrarOk('Miembro creado');
                await this.cargarAjustes();
            } catch (e) {
                this.mostrarError('Error: ' + e.message);
            }
        },

        async guardarCuenta() {
            try {
                const datos = { ...this.nuevaCuenta };
                if (datos.miembro_id) datos.miembro_id = parseInt(datos.miembro_id);
                await API.crear('/cuentas', datos);
                this.nuevaCuenta = { nombre: '', banco: '', miembro_id: '', es_compartida: false };
                this.mostrarOk('Cuenta creada');
                await this.cargarAjustes();
                await this.cargarDatosMaestros();
            } catch (e) {
                this.mostrarError('Error: ' + e.message);
            }
        },

        editarCuenta(cuenta) {
            this.editandoCuenta = { ...cuenta, miembro_id: cuenta.miembro_id || '' };
        },

        cancelarEdicionCuenta() {
            this.editandoCuenta = null;
        },

        async actualizarCuenta() {
            try {
                const datos = { ...this.editandoCuenta };
                datos.miembro_id = datos.miembro_id ? parseInt(datos.miembro_id) : null;
                delete datos.id;
                delete datos.creado_en;
                await API.actualizar(`/cuentas/${this.editandoCuenta.id}`, datos);
                this.editandoCuenta = null;
                this.mostrarOk('Cuenta actualizada');
                await this.cargarAjustes();
                await this.cargarDatosMaestros();
            } catch (e) {
                this.mostrarError('Error: ' + e.message);
            }
        },

        async borrarCuenta(cuenta) {
            if (!confirm(`¿Eliminar la cuenta "${cuenta.nombre}"? Los movimientos asociados quedarán sin cuenta.`)) return;
            try {
                await API.borrar(`/cuentas/${cuenta.id}`);
                this.mostrarOk('Cuenta eliminada');
                await this.cargarAjustes();
                await this.cargarDatosMaestros();
            } catch (e) {
                this.mostrarError('Error: ' + e.message);
            }
        },

        async borrarMapeo(id) {
            if (!confirm('¿Eliminar este mapeo de tarjeta?')) return;
            try {
                await API.borrar(`/mapeo-tarjetas/${id}`);
                this.mostrarOk('Mapeo eliminado');
                await this.cargarAjustes();
            } catch (e) {
                this.mostrarError('Error: ' + e.message);
            }
        },

        async guardarMapeo() {
            try {
                await API.crear('/mapeo-tarjetas', {
                    ultimos4: this.nuevoMapeo.ultimos4,
                    cuenta_id: parseInt(this.nuevoMapeo.cuenta_id),
                    etiqueta: this.nuevoMapeo.etiqueta,
                });
                this.nuevoMapeo = { ultimos4: '', cuenta_id: '', etiqueta: '' };
                this.mostrarOk('Mapeo creado');
                await this.cargarAjustes();
            } catch (e) {
                this.mostrarError('Error: ' + e.message);
            }
        },

        async guardarVinculacion() {
            try {
                await API.crear('/transferencias/vinculaciones', {
                    cuenta_principal_id: parseInt(this.nuevaVinculacion.cuenta_principal_id),
                    cuenta_vinculada_id: parseInt(this.nuevaVinculacion.cuenta_vinculada_id),
                    patron_principal:    this.nuevaVinculacion.patron_principal,
                    patron_vinculada:    this.nuevaVinculacion.patron_vinculada,
                    tolerancia_dias:     parseInt(this.nuevaVinculacion.tolerancia_dias) || 1,
                });
                this.nuevaVinculacion = { cuenta_principal_id: '', cuenta_vinculada_id: '', patron_principal: 'Recarga', patron_vinculada: 'Recargas: Pago de%', tolerancia_dias: 1 };
                this.mostrarOk('Vinculación creada');
                await this.cargarAjustes();
            } catch (e) {
                this.mostrarError('Error: ' + e.message);
            }
        },

        async borrarVinculacion(id) {
            if (!confirm('¿Eliminar esta vinculación? Los movimientos ya marcados como transferencia interna no se desmarcarán.')) return;
            try {
                await API.borrar(`/transferencias/vinculaciones/${id}`);
                this.mostrarOk('Vinculación eliminada');
                await this.cargarAjustes();
            } catch (e) {
                this.mostrarError('Error: ' + e.message);
            }
        },

        // ---- CRYPTO ----
        async cargarCrypto() {
            this.cargandoCrypto = true;
            this.errorCrypto = '';
            this.grafica24 = null;
            // Cargar portfolio — muestra la tabla en cuanto llegue
            try {
                const resp = await fetch('/crypto/api/portafolio');
                if (!resp.ok) throw new Error('HTTP ' + resp.status);
                this.portafolioCrypto = await resp.json() || [];
            } catch (e) {
                this.errorCrypto = 'No se pudo conectar con Kryptonite (' + e.message + ')';
                this.portafolioCrypto = [];
            } finally {
                this.cargandoCrypto = false;
            }
            // Cargar gráfica en segundo plano — puede tardar varios segundos
            fetch('/crypto/api/grafica24h')
                .then(r => r.json())
                .then(datos => { this.grafica24 = datos?.chart || null; })
                .catch(() => {});
        },

        totalCryptoInvertido() {
            return this.portafolioCrypto.reduce((s, c) => s + c.coste_total_inversion, 0);
        },

        totalCryptoValor() {
            return this.portafolioCrypto.reduce((s, c) => s + c.valor_actual_inversion, 0);
        },

        totalCryptoPct() {
            const inv = this.totalCryptoInvertido();
            return inv > 0 ? ((this.totalCryptoValor() - inv) / inv * 100) : 0;
        },

        fmtNum(n) {
            return Math.round(n).toLocaleString('es-ES');
        },

        emojiCrypto(simbolo) {
            const emojis = { BTC: '₿', ETH: 'Ξ', ADA: '💠', DOT: '⚫', SHIB: '🐶', SOL: '☀️', XRP: '💧' };
            return emojis[simbolo] || '🪙';
        },

        // ---- UTILIDADES ----
        formatoImporte(valor) {
            return new Intl.NumberFormat('es-ES', {
                style: 'currency', currency: 'EUR',
                minimumFractionDigits: 2,
            }).format(valor);
        },

        nombreCategoria(categoriaId) {
            if (!categoriaId) return 'Sin categoría';
            const cat = this.categoriasPlanas.find(c => c.id === categoriaId);
            if (!cat) return 'Sin categoría';
            if (cat.padre_id) {
                const padre = this.categoriasPlanas.find(c => c.id === cat.padre_id);
                return padre ? padre.nombre + ' > ' + cat.nombre : cat.nombre;
            }
            return cat.nombre;
        },

        // Solo subcategorías (nivel 2) para los selects
        subcategorias() {
            return this.categoriasPlanas.filter(c => c.padre_id !== null);
        },

        /**
         * Categorías agrupadas por padre con hijas ordenadas alfabéticamente.
         * Devuelve el array jerárquico (this.categorias) con las hijas
         * ordenadas por nombre para usar en <optgroup>.
         */
        categoriasAgrupadas() {
            return this.categorias
                .slice()
                .sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'))
                .map(padre => ({
                    ...padre,
                    hijas: padre.hijas
                        .slice()
                        .sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'))
                }));
        },

        mostrarOk(texto) {
            this.mensaje = texto;
            this.tipoMensaje = 'ok';
            setTimeout(() => this.mensaje = '', 3000);
        },

        mostrarError(texto) {
            this.mensaje = texto;
            this.tipoMensaje = 'error';
            setTimeout(() => this.mensaje = '', 5000);
        },

        // Cambiar de pestaña y cargar datos
        async irA(pestana) {
            this.pestana = pestana;
            if (pestana === 'panel') await this.cargarPanel();
            if (pestana === 'movimientos') await this.cargarMovimientos();
            if (pestana === 'categorias') await this.cargarCategorias();
            if (pestana === 'reglas') await this.cargarReglas();
            if (pestana === 'ajustes') await this.cargarAjustes();
            if (pestana === 'crypto') await this.cargarCrypto();
        },
    };
}
