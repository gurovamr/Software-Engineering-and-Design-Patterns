(function () {
    const graphIds = ["trackmap-graph", "gear-map-graph"];
    const overlayMeta = "sedpCrossHover";
    const state = { syncing: false, lastHoverAt: 0, lastDistanceByGraph: {} };

    function asNumber(value) {
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : null;
    }

    function graphDiv(id) {
        const outer = document.getElementById(id);
        if (!outer) return null;
        if (outer.data && outer.layout) return outer;
        return outer.querySelector(".js-plotly-plot");
    }

    function customAt(trace, pointNumber) {
        const rows = trace && trace.customdata ? trace.customdata : [];
        return rows[pointNumber] || [];
    }

    function labelFromCustom(custom) {
        return custom && custom.length >= 1 ? String(custom[0]) : "";
    }

    function distanceFromCustom(custom) {
        return custom && custom.length >= 4 ? asNumber(custom[3]) : null;
    }

    function metricBadge(custom) {
        const label = labelFromCustom(custom);
        const lap = custom && custom.length >= 3 ? asNumber(custom[2]) : null;
        const distance = distanceFromCustom(custom);
        const speed = custom && custom.length >= 5 ? asNumber(custom[4]) : null;
        const throttle = custom && custom.length >= 6 ? asNumber(custom[5]) : null;
        const brake = custom && custom.length >= 7 ? custom[6] : null;
        const gear = custom && custom.length >= 8 ? asNumber(custom[7]) : null;
        const parts = [label];

        if (lap !== null) parts.push(`Lap ${lap.toFixed(0)}`);
        if (distance !== null) parts.push(`${distance.toFixed(0)} m`);
        if (speed !== null) parts.push(`${speed.toFixed(1)} km/h`);
        if (throttle !== null) parts.push(`${throttle.toFixed(0)}% throttle`);
        if (brake !== null && String(brake) !== "") parts.push(`Brake: ${brake}`);
        if (gear !== null) parts.push(`Gear ${gear.toFixed(0)}`);

        return parts.join("<br>");
    }

    function removeOverlays(gd) {
        if (!window.Plotly || !gd || !gd.data) return Promise.resolve();

        const indices = [];
        gd.data.forEach((trace, index) => {
            if (trace.meta && trace.meta[overlayMeta]) {
                indices.push(index);
            }
        });

        if (!indices.length) return Promise.resolve();

        indices.sort((a, b) => b - a);
        return window.Plotly.deleteTraces(gd, indices).catch(() => undefined);
    }

    function originalTraceIndices(gd) {
        const indices = [];
        if (!gd || !gd.data) return indices;
        gd.data.forEach((trace, index) => {
            if (!(trace.meta && trace.meta[overlayMeta])) {
                indices.push(index);
            }
        });
        return indices;
    }

    function clearSelectedPoints(gd) {
        if (!window.Plotly || !gd || !gd.data) return Promise.resolve();
        const indices = originalTraceIndices(gd);
        if (!indices.length) return Promise.resolve();
        return window.Plotly.restyle(gd, { selectedpoints: [null] }, indices).catch(() => undefined);
    }

    function baseAnnotations(gd) {
        const annotations = (gd && gd.layout && gd.layout.annotations) ? gd.layout.annotations : [];
        return annotations.filter((annotation) => annotation.name !== overlayMeta);
    }

    function clearMetricAnnotations(gd) {
        if (!window.Plotly || !gd) return Promise.resolve();
        return window.Plotly.relayout(gd, { annotations: baseAnnotations(gd) }).catch(() => undefined);
    }

    function pointNumber(point) {
        if (!point) return null;
        if (point.pointNumber !== undefined) return point.pointNumber;
        if (point.pointIndex !== undefined) return point.pointIndex;
        if (point.pointNumbers && point.pointNumbers.length) return point.pointNumbers[0];
        return null;
    }

    function nearestPointsByDistance(gd, distance) {
        const bestByLabel = {};

        gd.data.forEach((trace, curveNumber) => {
            if (trace.meta && trace.meta[overlayMeta]) return;

            const rows = Array.from(trace.customdata || []);
            rows.forEach((custom, pointIndex) => {
                const label = labelFromCustom(custom);
                const pointDistance = distanceFromCustom(custom);

                if (!label || pointDistance === null) return;

                const delta = Math.abs(pointDistance - distance);

                if (bestByLabel[label] && delta >= bestByLabel[label].delta) return;

                bestByLabel[label] = {
                    label,
                    curveNumber,
                    pointNumber: pointIndex,
                    delta,
                    x: trace.x ? trace.x[pointIndex] : null,
                    y: trace.y ? trace.y[pointIndex] : null,
                    xaxis: trace.xaxis || "x",
                    yaxis: trace.yaxis || "y",
                    custom,
                };
            });
        });

        return Object.values(bestByLabel).filter((point) => point.x !== null && point.y !== null);
    }

    function addOverlays(gd, points) {
        if (!window.Plotly || !gd || !points.length) return Promise.resolve();

        const traces = points.map((point) => ({
            type: "scatter",
            mode: "markers+text",
            x: [point.x],
            y: [point.y],
            xaxis: point.xaxis,
            yaxis: point.yaxis,
            marker: {
                size: 18,
                color: "rgba(255,255,255,0)",
                line: { color: "#fbbf24", width: 3 },
            },
            text: [metricBadge(point.custom)],
            textposition: "top center",
            textfont: { color: "#fbbf24", size: 11, family: "monospace" },
            hoverinfo: "skip",
            showlegend: false,
            cliponaxis: false,
            meta: { [overlayMeta]: true },
            name: "Cross-hover point",
        }));

        return window.Plotly.addTraces(gd, traces).catch(() => undefined);
    }

    function addMetricAnnotations(gd, points) {
        if (!window.Plotly || !gd || !points.length) return Promise.resolve();

        const annotations = baseAnnotations(gd).concat(points.map((point) => ({
            x: point.x,
            y: point.y,
            xref: point.xaxis || "x",
            yref: point.yaxis || "y",
            text: metricBadge(point.custom),
            showarrow: true,
            arrowhead: 2,
            arrowwidth: 1.5,
            arrowcolor: "#fbbf24",
            ...annotationOffset(gd, point),
            align: "left",
            bgcolor: "rgba(17, 24, 39, 0.96)",
            bordercolor: "#fbbf24",
            borderpad: 4,
            borderwidth: 1,
            font: { color: "#ffffff", size: 11, family: "monospace" },
            name: overlayMeta,
        })));

        return window.Plotly.relayout(gd, { annotations }).catch(() => undefined);
    }

    function axisLayout(gd, axisRef) {
        if (!gd || !gd._fullLayout || !axisRef) return null;
        const axisName = axisRef.length === 1 ? `${axisRef}axis` : `${axisRef[0]}axis${axisRef.slice(1)}`;
        return gd._fullLayout[axisName] || null;
    }

    function axisDomainCenter(axis) {
        if (!axis || !axis.domain || axis.domain.length < 2) return 0.5;
        const start = asNumber(axis.domain[0]);
        const end = asNumber(axis.domain[1]);
        if (start === null || end === null) return 0.5;
        return (start + end) / 2;
    }

    function annotationOffset(gd, point) {
        const xAxis = axisLayout(gd, point.xaxis || "x");
        const ax = axisDomainCenter(xAxis) > 0.5 ? -200 : 200;
        const ay = -42;
        return { ax, ay };
    }

    function selectNearestPoints(gd, points) {
        if (!window.Plotly || !gd || !points.length) return Promise.resolve();

        const byTrace = {};
        points.forEach((point) => {
            byTrace[point.curveNumber] = [point.pointNumber];
        });

        const updates = Object.entries(byTrace).map(([curveNumber, selected]) => (
            window.Plotly.restyle(
                gd,
                {
                    selectedpoints: [selected],
                    selected: [{
                        marker: {
                            size: 14,
                            color: "#fbbf24",
                            line: { color: "#ffffff", width: 2 },
                        },
                    }],
                    unselected: [{ marker: { opacity: 0.45 } }],
                },
                [Number(curveNumber)]
            ).catch(() => undefined)
        ));

        return Promise.all(updates);
    }

    function hoverDistance(gd, eventData) {
        if (!eventData || !eventData.points || !eventData.points.length) return null;
        const point = eventData.points[0];
        const index = pointNumber(point);
        const trace = gd.data && point.curveNumber !== undefined ? gd.data[point.curveNumber] : point.data;
        const custom = point.customdata || customAt(trace, index);
        const distance = distanceFromCustom(custom);
        return distance === null ? asNumber(point.x) : distance;
    }

    function syncAtDistance(gd, distance) {
        if (!window.Plotly || state.syncing) return;
        if (distance === null) return;

        state.syncing = true;
        state.lastHoverAt = Date.now();

        const points = nearestPointsByDistance(gd, distance);

        Promise.all([removeOverlays(gd), clearSelectedPoints(gd), clearMetricAnnotations(gd)])
            .then(() => Promise.all([
                selectNearestPoints(gd, points),
                addOverlays(gd, points),
                addMetricAnnotations(gd, points),
            ]))
            .finally(() => {
                window.setTimeout(() => {
                    state.syncing = false;
                }, 30);
            });
    }

    function syncHover(gd, eventData) {
        const distance = hoverDistance(gd, eventData);
        syncAtDistance(gd, distance);
    }

    function clearHover(gd) {
        if (!gd) return Promise.resolve();
        const hoverAt = Date.now();
        state.lastHoverAt = hoverAt;

        window.setTimeout(() => {
            if (state.lastHoverAt === hoverAt) {
                Promise.all([removeOverlays(gd), clearSelectedPoints(gd), clearMetricAnnotations(gd)]);
            }
        }, 250);
    }

    function triggeredGraphId() {
        const ctx = window.dash_clientside && window.dash_clientside.callback_context;
        const triggered = ctx && ctx.triggered && ctx.triggered[0] ? ctx.triggered[0].prop_id : "";
        return triggered ? triggered.split(".")[0] : "";
    }

    function syncFromDash(trackHover, gearHover) {
        const graphId = triggeredGraphId();
        const isGear = graphId === "gear-map-graph";
        const isTrack = graphId === "trackmap-graph";
        const activeGraphId = isGear || isTrack ? graphId : (trackHover ? "trackmap-graph" : "gear-map-graph");
        const hoverData = activeGraphId === "gear-map-graph" ? gearHover : trackHover;
        const gd = graphDiv(activeGraphId);

        if (!gd) return window.dash_clientside.no_update;
        if (!hoverData || !hoverData.points || !hoverData.points.length) {
            return Date.now();
        }

        syncAtDistance(gd, hoverDistance(gd, hoverData));
        return Date.now();
    }

    function attach(gd, id) {
        if (!gd || !gd.on) return;

        const signature = `${id}:${gd.data ? gd.data.length : 0}`;
        if (gd.__sedpTrackHoverSignature === signature && gd.__sedpTrackHoverAttached) return;

        if (gd.__sedpTrackHoverHoverHandler && gd.removeListener) {
            gd.removeListener("plotly_hover", gd.__sedpTrackHoverHoverHandler);
        }
        if (gd.__sedpTrackHoverUnhoverHandler && gd.removeListener) {
            gd.removeListener("plotly_unhover", gd.__sedpTrackHoverUnhoverHandler);
        }
        if (gd.__sedpTrackHoverMouseLeaveHandler && gd.removeEventListener) {
            gd.removeEventListener("mouseleave", gd.__sedpTrackHoverMouseLeaveHandler);
        }

        gd.__sedpTrackHoverSignature = signature;
        gd.__sedpTrackHoverAttached = true;
        resizeWhenReady(gd);
        gd.__sedpTrackHoverHoverHandler = (eventData) => {
            state.lastDistanceByGraph[id] = hoverDistance(gd, eventData);
            syncAtDistance(gd, state.lastDistanceByGraph[id]);
        };
        gd.__sedpTrackHoverUnhoverHandler = null;
        gd.__sedpTrackHoverMouseLeaveHandler = () => clearHover(gd);
        gd.on("plotly_hover", gd.__sedpTrackHoverHoverHandler);
        gd.addEventListener("mouseleave", gd.__sedpTrackHoverMouseLeaveHandler);
    }

    function resizeWhenReady(gd) {
        if (!window.Plotly || !window.Plotly.Plots || !gd) return;
        [0, 100, 350, 900].forEach((delay) => {
            window.setTimeout(() => {
                try {
                    const resizeResult = window.Plotly.Plots.resize(gd);
                    if (resizeResult && resizeResult.catch) resizeResult.catch(() => undefined);

                    if (window.Plotly.redraw) {
                        const redrawResult = window.Plotly.redraw(gd);
                        if (redrawResult && redrawResult.catch) redrawResult.catch(() => undefined);
                    }
                } catch (_error) {
                    // Ignore transient redraw errors while Dash is replacing the graph.
                }
            }, delay);
        });
    }

    function scan() {
        graphIds.forEach((id) => {
            const gd = graphDiv(id);
            if (gd) attach(gd, id);
        });
    }

    document.addEventListener("DOMContentLoaded", scan);
    window.setInterval(scan, 1000);

    window.dash_clientside = Object.assign({}, window.dash_clientside, {
        sedpTrackHover: {
            sync: syncFromDash,
        },
    });
})();
