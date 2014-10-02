
var marajax = (function () {
    'use strict';

    function Marajax() {
        var that = {}, req = null;
        if (window.XMLHttpRequest) {
            try {
                req = new XMLHttpRequest();
            } catch (e) {
                throw {
                    name: 'ObjectNotFoundError',
                    message: 'This application requires a browser with XML support.'
                };
            }
        } else {
            throw {
                name: 'TypeError',
                message: 'This application requires a browser with XML support.'
            };
        }
        that.request = req;
        that.go = function (o) {
            if (!o.url) {
                throw {
                    name: "MissingURLError",
                    message: "URL must be provided in order to execute a request."
                };
            }
            var n = {};
            n.url = o.url;
            n.async = o.async || true;
            n.success = o.success || function (c) {
                console.log('Non implemented success: ' + JSON.stringify(c));
            };
            n.fail = o.fail || function (c) {
                console.log('Non implemented fail: ' + JSON.stringify(c));
            };
            n.queryString = that.queryString(o.params || null);
            n.output = o.output || 'text';
            n.post = o.post || false;
            if (n.post) {
                that.post(n);
            } else {
                if (n.queryString) n.url += '?' + n.queryString;
                that.get(n);
            }
        };
        that.get = function (config) {
            that.request.onreadystatechange = that.responseProcessor(config);
            that.request.open('GET', config.url, config.async);
            that.request.send(null);
        };
        that.post = function (config) {
            // that.request.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");
            that.request.onreadystatechange = that.responseProcessor(config);
            that.request.open('POST', config.url, config.async);
            that.request.send(config.queryString);
        };
        that.responseProcessor = function (config) {
            return function() {
                if (that.request.readyState === 4) {
                    if (that.request.status === 200) {
                        if (config.output === 'text') {
                            config.success(that.request.responseText);
                        } else if (config.output === 'json') {
                            config.success(JSON.parse(that.request.responseText));
                        } else if (config.output === 'xml') {
                            config.success(that.request.responseXML);
                        }
                    } else {
                        config.fail({
                            state: that.request.readyState,
                            status: that.request.status,
                            statusText: that.request.statusText
                        });
                    }
                }
            };
        };
        that.queryString = function (obj) {
            var q = "",
                key;
            if (obj) {
                for (key in obj) {
                    if (obj.hasOwnProperty(key)) {
                        q += key + "=" + encodeURIComponent(obj[key]) + "&";
                    }
                }
            }
            return q;
        };
        return that;
    };
    var marajax = new Marajax();
    return {
        go: marajax.go,
        queryString: marajax.queryString,
        Marajax: Marajax,
    };
}());

