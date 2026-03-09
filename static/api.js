/**
 * FiDo — Cliente API (wrappers sobre fetch).
 */
const API = {
    /** Construye la URL completa de la API. */
    _url(ruta) {
        return `/api${ruta}`;
    },

    async obtener(ruta) {
        const resp = await fetch(this._url(ruta));
        if (!resp.ok) throw new Error(await resp.text());
        return resp.json();
    },

    async crear(ruta, datos) {
        const resp = await fetch(this._url(ruta), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(datos),
        });
        if (!resp.ok) throw new Error(await resp.text());
        return resp.json();
    },

    async actualizar(ruta, datos) {
        const resp = await fetch(this._url(ruta), {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(datos),
        });
        if (!resp.ok) throw new Error(await resp.text());
        return resp.json();
    },

    async borrar(ruta) {
        const resp = await fetch(this._url(ruta), { method: 'DELETE' });
        if (!resp.ok && resp.status !== 204) throw new Error(await resp.text());
        return true;
    },

    async subirCSV(fichero, cuentaId, banco) {
        const formulario = new FormData();
        formulario.append('fichero', fichero);
        formulario.append('cuenta_id', cuentaId);
        formulario.append('banco', banco);
        const resp = await fetch(this._url('/importar/csv'), {
            method: 'POST',
            body: formulario,
        });
        if (!resp.ok) throw new Error(await resp.text());
        return resp.json();
    },
};
