/**
 * FiDo — Componente Alpine.js principal.
 * Gestiona toda la lógica del frontend SPA.
 */
function fidoApp() {
    return {
        // Navegación
        pestana: 'panel',

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
        filtros: { mes: '', cuenta_id: '', categoria_id: '', buscar: '', offset: 0 },
        editandoMovimiento: null,
        mostrarFormularioMovimiento: false,
        nuevoMovimiento: { fecha: '', importe: '', descripcion: '', cuenta_id: '', categoria_id: '', origen: 'web', notas: '' },

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

        // Formularios
        nuevaRegla: { patron: '', categoria_id: '', prioridad: 0 },
        nuevoMiembro: { nombre: '', telegram_chat_id: '' },
        nuevaCuenta: { nombre: '', banco: '', miembro_id: '', es_compartida: false },
        editandoCuenta: null,
        nuevoMapeo: { ultimos4: '', cuenta_id: '', etiqueta: '' },

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
            const canvas = document.getElementById('graficaCategoria');
            if (!canvas || !this.datosPorCategoria.length) return;
            if (this.graficaCategoria) this.graficaCategoria.destroy();

            const colores = [
                '#3B82F6', '#EF4444', '#10B981', '#F59E0B', '#8B5CF6',
                '#EC4899', '#06B6D4', '#84CC16', '#F97316', '#6366F1',
                '#14B8A6', '#E11D48', '#A855F7',
            ];

            this.graficaCategoria = new Chart(canvas, {
                type: 'doughnut',
                data: {
                    labels: this.datosPorCategoria.map(c => (c.icono || '') + ' ' + c.nombre),
                    datasets: [{
                        data: this.datosPorCategoria.map(c => Math.round(c.total * 100) / 100),
                        backgroundColor: colores,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'right', labels: { font: { size: 11 } } },
                    },
                },
            });
        },

        renderizarGraficaMes() {
            const canvas = document.getElementById('graficaMes');
            if (!canvas || !this.datosPorMes.length) return;
            if (this.graficaMes) this.graficaMes.destroy();

            this.graficaMes = new Chart(canvas, {
                type: 'bar',
                data: {
                    labels: this.datosPorMes.map(m => m.mes),
                    datasets: [
                        {
                            label: 'Ingresos',
                            data: this.datosPorMes.map(m => m.ingresos),
                            backgroundColor: '#10B981',
                        },
                        {
                            label: 'Gastos',
                            data: this.datosPorMes.map(m => m.gastos),
                            backgroundColor: '#EF4444',
                        },
                    ],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: { y: { beginAtZero: true } },
                    plugins: { legend: { position: 'top' } },
                },
            });
        },

        // ---- MOVIMIENTOS ----
        async cargarMovimientos() {
            try {
                const params = new URLSearchParams();
                if (this.filtros.mes) params.set('mes', this.filtros.mes);
                if (this.filtros.cuenta_id) params.set('cuenta_id', this.filtros.cuenta_id);
                if (this.filtros.categoria_id) params.set('categoria_id', this.filtros.categoria_id);
                if (this.filtros.buscar) params.set('buscar', this.filtros.buscar);
                params.set('offset', this.filtros.offset);
                params.set('limite', '50');
                const qs = '?' + params.toString();

                [this.movimientos, { total: this.totalMovimientos }] = await Promise.all([
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
            };
            this.mostrarFormularioMovimiento = true;
        },

        cancelarEdicionMovimiento() {
            this.editandoMovimiento = null;
            this.mostrarFormularioMovimiento = false;
            const hoy = new Date().toISOString().split('T')[0];
            this.nuevoMovimiento = { fecha: hoy, importe: '', descripcion: '', cuenta_id: '', categoria_id: '', origen: 'web', notas: '' };
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
        },
    };
}
