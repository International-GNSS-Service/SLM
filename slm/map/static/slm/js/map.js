class SLMSiteMap {
    constructor(options, source=slm.urls.reverse('slm_edit_api:map-list')) {
        this.element = $(`#${options["container"]}`);
        this.map = new mapboxgl.Map(options);
        $(this.element).mousedown(function (e) {
            e.stopPropagation();
        });
        this.hoveredStation = null;
        this.selectedStation = null;
        this.selectCallback = null;
        this.clickCoords = {x:-1, y:-1};
        const baseRadius = [
            'interpolate',
            ['linear'],
            ['zoom'],
            0,
            [
                'case',
                ['boolean', ['feature-state', 'selected'], false],
                ['+', 2.5, 3],
                ['case',
                    ['boolean', ['feature-state', 'hover'], false],
                    ['+', 2.5, 3],
                    2.5
                ]
            ],
            22,
            [
                'case',
                ['boolean', ['feature-state', 'selected'], false],
                ['+', 15, 3],
                ['case',
                    ['boolean', ['feature-state', 'hover'], false],
                    ['+', 15, 3],
                    15
                ]
            ]
        ];
        this.map.on('load', function () {
            this.setSource(source);
            this.map.addLayer({
                'id': 'station_layer',
                'type': 'circle',
                'source': 'stations',
                'paint': {
                    'circle-radius': baseRadius,
                    'circle-color': [
                        'match',
                        ['get', 'status'],
                        slm.SiteLogStatus.FORMER.value,
                        slm.SiteLogStatus.FORMER.color,
                        slm.SiteLogStatus.SUSPENDED.value,
                        slm.SiteLogStatus.SUSPENDED.color,
                        slm.SiteLogStatus.PROPOSED.value,
                        slm.SiteLogStatus.PROPOSED.color,
                        slm.SiteLogStatus.UPDATED.value,
                        slm.SiteLogStatus.UPDATED.color,
                        slm.SiteLogStatus.PUBLISHED.value,
                        slm.SiteLogStatus.PUBLISHED.color,
                        '#223B53'
                    ],
                    'circle-opacity': 1
                }
            });
        }.bind(this));

        this.map.on(
            'mousemove',
            'station_layer', function(e) {
                if (e.features.length > 0) {
                    if (this.hoveredStation !== null) {
                        this.map.setFeatureState(
                            { source: 'stations', id: this.hoveredStation },
                            { hover: false }
                        );
                    }
                    this.hoveredStation = e.features[0].id;
                    this.map.setFeatureState(
                        { source: 'stations', id: this.hoveredStation },
                        { hover: true }
                    );
                    let div = $('#site-name');
                    div.html(e.features[0].properties['name']);
                    div.attr('style', `color: ${SiteLogStatus.get(e.features[0].properties['status']).color}`);
                }
            }.bind(this)
        );

        // When the mouse leaves the state-fill layer, update the feature state of the
        // previously hovered feature.
        this.map.on(
            'mouseleave',
            'station_layer', function() {
                if (this.hoveredStation !== null) {
                    this.map.setFeatureState(
                        { source: 'stations', id: this.hoveredStation },
                        { hover: false }
                    );
                }
                if (this.hoveredStation) {
                    $('#site-name').html('');
                    this.hoveredStation = null;
                }
            }.bind(this)
        );

        this.map.on(
            'click',
            function(e) {
                if (
                    this.selectedStation !== null &&
                    this.clickCoords.x !== e.point.x &&
                    this.clickCoords.y !== e.point.y
                )
                {
                    this.map.setFeatureState(
                        { source: 'stations', id: this.selectedStation },
                        { selected: false }
                    );
                }
                this.selectCallback('');
            }.bind(this)
        );
        this.map.on(
            'click',
            'station_layer',
            function(e) {
                this.clickCoords = e.point;
                if (this.selectedStation !== null) {
                    this.map.setFeatureState(
                        { source: 'stations', id: this.selectedStation },
                        { selected: false }
                    );
                }
                this.selectedStation = e.features[0].id;
                this.map.setFeatureState(
                    { source: 'stations', id: this.selectedStation },
                    { selected: true }
                );
                this.selectCallback(e.features[0].properties['name']);
            }.bind(this)
        );
    }

    setSelectCallback(callback) {
        this.selectCallback = callback;
    }

    setSource(mapQuery) {
        if (this.map.getSource('stations')) {
            this.map.getSource('stations').setData(mapQuery);
        } else {
            this.map.addSource('stations', {
                type: 'geojson',
                data: mapQuery
            });
        }
    }
}
