// go.components.structures
// ========================
// Reusable, generic structures for Go

(function(exports) {
  var merge = go.utils.merge;

  // Acts as a 'base' for class-like objects which can be extended (with the
  // prototype chain set up automatically)
  exports.Extendable = function () {};

  exports.Extendable.extend = function() {
    // Backbone has an internal `extend()` function which it assigns to its
    // structures. We need this function, so we arbitrarily choose
    // `Backbone.Model`, since it has the function we are looking for.
    return Backbone.Model.extend.call(this, merge.apply(this, arguments));
  };

  // A class-like object onto which events can be bound and emitted
  exports.Eventable = exports.Extendable.extend(Backbone.Events);

  // A structure that stores key-value pairs, provides helpful operations for
  // accessing the data, and emits events when items are added or removed.
  // Similar to a Backbone Collection, except the contents are key-value pairs
  // instead of models.
  //
  // Arguments:
  //   - items: the initial objects to be added
  //
  // Events emitted:
  //   - 'add' (key, value) - Emitted when an item is added
  //   - 'remove' (key, value) - Emitted when an item is removed
  var Lookup = exports.Lookup = exports.Eventable.extend({
    constructor: function(items) {
      this._items = {};

      items = items || {};
      for (var k in items) { this.add(k, items[k]); }
    },

    keys: function() { return _.keys(this._items); },
    values: function() { return _.values(this._items); },
    items: function() { return _.clone(this._items); },

    get: function(key) { return this._items[key] || null; },

    add: function(key, value) {
      this._items[key] = value;
      this.trigger('add', key, value);
      return this;
    },

    remove: function(key) {
      var value = this._items[key];
      if (value) {
        delete this._items[key];
        this.trigger('remove', key, value);
      }
      return value;
    }
  });

  // Accepts a collection of models and maintains a corresponding collection of
  // views. New views are created when models are added to the collection, old
  // views are removed when models are removed from the collection. Views can
  // also be looked up by the id of their corresponding models. Useful in
  // situations where views are to be created dynamically (for eg, state views
  // in a state machine diagram).
  //
  // Arguments:
  //   - collection: the collection of models to create views for
  //
  // Events emitted:
  //   - 'add' (id, view) - Emitted when a view is added
  //   - 'remove' (id, view) - Emitted when a view is removed
  exports.ViewCollection = Lookup.extend({
    constructor: function(collection) {
      Lookup.prototype.constructor.call(this);
      _.bindAll(this);

      this.models = collection;
      this._modelIds().forEach(this.add);

      this.models.on('add', this.render);
      this.models.on('remove', this.render);
    },

    _modelId: function(m) { return m.id; },
    _modelIds: function(m) { return this.models.map(this._modelId); },

    // Override to specialise how the view is created
    create: function(model) { return new Backbone.View({model: model}); },

    add: function(id) {
      Lookup.prototype.add.call(this, id, this.create(this.models.get(id)));
    },

    remove: function(id) {
      var view = Lookup.prototype.remove.call(this, id);
      if (view && typeof view.destroy === 'function') { view.destroy(); }
      return view;
    },

    render: function() {
      var modelIds = this._modelIds(),
          viewIds = this.keys();

      // Remove 'dead' views
      // (views with models that no longer exist)
      _.difference(viewIds, modelIds)
       .forEach(this.remove);

      // Add 'new' view
      // (models with no corresponding views)
      _.difference(modelIds, viewIds)
       .forEach(this.add);

      this.values().forEach(function(v) { v.render(); });
    }
  });
})(go.components.structures = {});