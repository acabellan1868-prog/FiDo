/**
 * FiDo — Componente Alpine.js principal.
 * Gestiona toda la lógica del frontend SPA.
 *
 * Rediseño Cockpit (2026-05): sustituye ApexCharts por SVG vanilla.
 * Añade helpers catColor() y catPct() para las minibars del panel.
 */

/** Paleta de colores compartida entre minibars, donut y distribución crypto. */
var COLORES_CAT = [
    '#00e5c4', '#6366f1', '#f59e0b', '#ec4899',
    '#06b6d4', '#84cc16', '#f97316', '#a855f7',
];

function fidoApp() {
    return {
        // Navegación
        pestana: 'panel',
        drawerAbierto: false,

        // Estado del panel
        resumen: { ingresos: 0, gastos: 0, balance: 0, total_movimientos: 0 },
        datosPorCategoria: [],
        datosPorMes: [],
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
                    this.renderizarDonut();
                    this.renderizarBarras();
                });
            } catch (e) {
                this.mostrarError('Error cargando panel: ' + e.message);
            }
        },

        /**
         * Renderiza un donut SVG en #graficaCategoria con los datos de categorías.
         * Sustituye a ApexCharts para evitar dependencia externa.
         */
        renderizarDonut() {
            var el = document.getElementById('graficaCategoria');
            if (!el) return;
            var data = (this.datosPorCategoria || []).slice(0, 8);
            if (!data.length) { el.innerHTML = ''; return; }

            var total = data.reduce(function(s, d) { return s + d.total; }, 0);
            if (total <= 0) { el.innerHTML = ''; return; }

            var cx = 50, cy = 50, r = 35, stroke = 10;
            var cumAngle = -90;
            var paths = '';

            data.forEach(function(d, i) {
                var angle   = (d.total / total) * 360;
                var startA  = cumAngle * Math.PI / 180;
                var endA    = (cumAngle + angle) * Math.PI / 180;
                var x1 = cx + r * Math.cos(startA);
                var y1 = cy + r * Math.sin(startA);
                var x2 = cx + r * Math.cos(endA);
                var y2 = cy + r * Math.sin(endA);
                var large   = angle > 180 ? 1 : 0;
                var color   = COLORES_CAT[i % COLORES_CAT.length];
                paths += '<path d="M ' + x1.toFixed(2) + ' ' + y1.toFixed(2)
                    + ' A ' + r + ' ' + r + ' 0 ' + large + ' 1 '
                    + x2.toFixed(2) + ' ' + y2.toFixed(2)
                    + '" fill="none" stroke="' + color + '" stroke-width="' + stroke + '" />';
                cumAngle += angle;
            });

            var totalFmt = new Intl.NumberFormat('es-ES', {
                minimumFractionDigits: 0, maximumFractionDigits: 0,
            }).format(total);

            el.innerHTML = '<svg viewBox="0 0 100 100" style="width:100%;max-width:130px;overflow:visible">'
                + '<circle cx="' + cx + '" cy="' + cy + '" r="' + r
                + '" fill="none" stroke="rgba(0,229,196,0.12)" stroke-width="' + (stroke + 1) + '" />'
                + paths
                + '<text x="' + cx + '" y="' + (cy - 4)
                + '" text-anchor="middle" fill="#b8d8d0" font-family="JetBrains Mono,monospace" font-size="9" font-weight="700">'
                + totalFmt + '</text>'
                + '<text x="' + cx + '" y="' + (cy + 7)
                + '" text-anchor="middle" fill="#3a6058" font-family="JetBrains Mono,monospace" font-size="5.5">gastos €</text>'
                + '</svg>';
        },

        /**
         * Renderiza un gráfico de barras SVG en #graficaMes (ingresos vs gastos por mes).
         * Sustituye a ApexCharts para evitar dependencia externa.
         */
        renderizarBarras() {
            var el = document.getElementById('graficaMes');
            if (!el) return;
            var data = (this.datosPorMes || []).slice(-6);
            if (!data.length) { el.innerHTML = ''; return; }

            var H = 85, barW = 11, gap = 7, leftPad = 2;
            var maxVal = Math.max.apply(null, data.map(function(d) {
                return Math.max(d.ingresos || 0, d.gastos || 0);
            }));
            if (maxVal <= 0) maxVal = 1;

            var cols    = data.length;
            var totalW  = leftPad + gap + cols * (barW * 2 + gap);
            var bars    = '';

            data.forEach(function(d, i) {
                var x  = leftPad + gap + i * (barW * 2 + gap);
                var hI = ((d.ingresos || 0) / maxVal) * H;
                var hG = ((d.gastos   || 0) / maxVal) * H;
                bars += '<rect x="' + x + '" y="' + (H - hI).toFixed(1)
                    + '" width="' + barW + '" height="' + hI.toFixed(1)
                    + '" fill="#3ae8a0" opacity="0.75" rx="1" />';
                bars += '<rect x="' + (x + barW) + '" y="' + (H - hG).toFixed(1)
                    + '" width="' + barW + '" height="' + hG.toFixed(1)
                    + '" fill="#e85454" opacity="0.75" rx="1" />';
                var label = (d.mes || '').substring(0, 3);
                bars += '<text x="' + (x + barW).toFixed(1) + '" y="' + (H + 11)
                    + '" text-anchor="middle" fill="#3a6058"'
                    + ' font-family="JetBrains Mono,monospace" font-size="6">' + label + '</text>';
            });

            el.innerHTML = '<svg viewBox="0 0 ' + totalW + ' ' + (H + 16)
                + '" style="width:100%;overflow:visible">' + bars + '</svg>';
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

        async toggleTransferenciaInterna(mov) {
            try {
                const accion = mov.es_transferencia_interna ? 'desmarcar' : 'marcar';
                await API.crear(`/transferencias/${mov.id}/${accion}`, {});
                mov.es_transferencia_interna = mov.es_transferencia_interna ? 0 : 1;
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

        // ---- UTILIDADES DE PANEL ----

        /**
         * Devuelve el color de la paleta Cockpit para el índice i.
         * Usado en minibars, donut y distribución crypto.
         */
        catColor(i) {
            return COLORES_CAT[i % COLORES_CAT.length];
        },

        /**
         * Devuelve el porcentaje de 'cat' relativo al máximo de datosPorCategoria (0-100).
         */
        catPct(cat) {
            if (!this.datosPorCategoria.length) return 0;
            var max = this.datosPorCategoria[0].total;
            return max > 0 ? Math.min(100, (cat.total / max) * 100) : 0;
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
