// Common code to all tests
var snapshot = require('protractor-snapshot');

module.exports = {
    snapshot: function () {
        snapshot.source();
        snapshot.image();
    },
    log: function (e) {
        if ('map' in e) {
            e.map(
                function (e) {return [e.getTagName(), e.getText(), e.getLocation()];}
            ).then(function (v) {console.log(v);});
        }
        else {
            Promise.all([e.getTagName(), e.getText(), e.getLocation()]).then(
                function (v) {console.log(v);}
            );
        }
    }
};

by.addLocator(
    'cssExactText',
    function (cssSelector, exactText, using) {
        using = using || document;
        var elements = using.querySelectorAll(cssSelector);
        var matches = [];
        for (var i = 0; i < elements.length; ++i) {
            var element = elements[i];
            var elementText = (element.textContent || '').trim();
            if (elementText === exactText) {
                console.log(element.outerHTML);
                matches.push(element);
            }
        }
        return matches;
    }
);
