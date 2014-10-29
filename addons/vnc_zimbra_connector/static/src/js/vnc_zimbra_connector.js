openerp.vnc_zimbra_connector = function (instance) {
    var _t = instance.web._t,
       _lt = instance.web._lt;

    instance.mail.MessageCommon.include({
        init: function (parent, datasets, options) {
            var self = this;
            this._super(parent, datasets, options);
            // record options
            this.options = datasets.options || options || {};
            // record domain and context
            this.domain = datasets.domain || options.domain || [];
            this.context = _.extend({
                default_model: false,
                default_res_id: 0,
                default_parent_id: false }, options.context || {});
            this.id = datasets.id ||  false,
            this.last_id = this.id,
            this.model = datasets.model || this.context.default_model || false,
            this.res_id = datasets.res_id || this.context.default_res_id ||  false,
            this.parent_id = datasets.parent_id ||  false,
            this.type = datasets.type ||  false,
            this.subtype = datasets.subtype ||  false,
            this.is_author = datasets.is_author ||  false,
            this.is_private = datasets.is_private ||  false,
            this.subject = datasets.subject ||  false,
            this.name = datasets.name ||  false,
            this.record_name = datasets.record_name ||  false,
            this.body = datasets.body || '',
            this.email_to = datasets.email_to || '',
            this.email_cc = datasets.email_cc || '',
            this.email_from = datasets.email_from || '',
            this.vote_nb = datasets.vote_nb || 0,
            this.has_voted = datasets.has_voted ||  false,
            this.is_favorite = datasets.is_favorite ||  false,
            this.thread_level = datasets.thread_level ||  0,
            this.to_read = datasets.to_read || false,
            this.author_id = datasets.author_id || false,
            this.attachment_ids = datasets.attachment_ids ||  [],
            this.partner_ids = datasets.partner_ids || [];
            this.date = datasets.date;
            this.format_data();
            // record options and data
            this.show_record_name = this.options.show_record_name && this.record_name && !this.thread_level && this.model != 'res.partner';
            this.options.show_read = false;
            this.options.show_unread = false;
            if (this.options.show_read_unread_button) {
                if (this.options.read_action == 'read') this.options.show_read = true;
                else if (this.options.read_action == 'unread') this.options.show_unread = true;
                else {
                    this.options.show_read = this.to_read;
                    this.options.show_unread = !this.to_read;
                }
                this.options.rerender = true;
                this.options.toggle_read = true;
            }
            this.parent_thread = typeof parent.on_message_detroy == 'function' ? parent : this.options.root_thread;
            this.thread = false;
        },
    });
    
    
    /**
     * A mixin containing some useful methods to handle completion inputs.
     */
    instance.web.form.CompletionFieldMixin = {
    	    init: function() {
    	        this.limit = 7;
    	        this.orderer = new instance.web.DropMisordered();
    	    },
    	    /**
    	     * Call this method to search using a string.
    	     */
    	    get_search_result: function(search_val) {
    	        var self = this;

    	        var dataset = new instance.web.DataSet(this, this.field.relation, self.build_context());
    	        var blacklist = this.get_search_blacklist();
    	        this.last_query = search_val;

    	        return this.orderer.add(dataset.name_search(
    	                search_val, new instance.web.CompoundDomain(self.build_domain(), [["id", "not in", blacklist]]),
    	                'ilike', this.limit + 1, self.build_context())).then(function(data) {
    	            self.last_search = data;
    	            // possible selections for the m2o
    	            var values = _.map(data, function(x) {
    	                x[1] = x[1].split("\n")[0];
    	                return {
    	                    label: _.str.escapeHTML(x[1]),
    	                    value: x[1],
    	                    name: x[1],
    	                    id: x[0],
    	                };
    	            });

    	            // search more... if more results that max
    	            if (values.length > self.limit) {
    	                values = values.slice(0, self.limit);
    	                values.push({
    	                    label: _t("Search More..."),
    	                    action: function() {
    	                        dataset.name_search(search_val, self.build_domain(), 'ilike', false).done(function(data) {
    	                            self._search_create_popup("search", data);
    	                        });
    	                    },
    	                    classname: 'oe_m2o_dropdown_option'
    	                });
    	            }
    	            // quick create
    	            var raw_result = _(data.result).map(function(x) {return x[1];});
    	            if (search_val.length > 0 && !_.include(raw_result, search_val)) {
    	                values.push({
    	                    label: _.str.sprintf(_t('Create "<strong>%s</strong>"'),
    	                        $('<span />').text(search_val).html()),
    	                    action: function() {
    	                        self._quick_create(search_val);
    	                    },
    	                    classname: 'oe_m2o_dropdown_option'
    	                });
    	            }
    	            // create...
    	            values.push({
    	                label: _t("Create and Edit..."),
    	                action: function() {
    	                    self._search_create_popup("form", undefined, self._create_context(search_val));
    	                },
    	                classname: 'oe_m2o_dropdown_option'
    	            });

    	            return values;
    	        });
    	    },
    	    get_search_blacklist: function() {
    	        return [];
    	    },
    	    _quick_create: function(name) {
    	        var self = this;
    	        var slow_create = function () {
    	            self._search_create_popup("form", undefined, self._create_context(name));
    	        };
    	        if (self.options.quick_create === undefined || self.options.quick_create) {
    	            new instance.web.DataSet(this, this.field.relation, self.build_context())
    	                .name_create(name).done(function(data) {
    	                    self.add_id(data[0]);
    	                }).fail(function(error, event) {
    	                    event.preventDefault();
    	                    slow_create();
    	                });
    	        } else
    	            slow_create();
    	    },
    	    // all search/create popup handling
    	    _search_create_popup: function(view, ids, context) {
    	        var self = this;
    	        var pop = new instance.web.form.SelectCreatePopup(this);
    	        pop.select_element(
    	            self.field.relation,
    	            {
    	                title: (view === 'search' ? _t("Search: ") : _t("Create: ")) + this.string,
    	                initial_ids: ids ? _.map(ids, function(x) {return x[0]}) : undefined,
    	                initial_view: view,
    	                disable_multiple_selection: true
    	            },
    	            self.build_domain(),
    	            new instance.web.CompoundContext(self.build_context(), context || {})
    	        );
    	        pop.on("elements_selected", self, function(element_ids) {
    	            self.add_id(element_ids[0]);
    	            self.focus();
    	        });
    	    },
    	    /**
    	     * To implement.
    	     */
    	    add_id: function(id) {},
    	    _create_context: function(name) {
    	    	console.log("MY FUNCTION CALLEDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDd")
    	    	var tmp = {};
    	    	if(this.name == 'partner_id'){
    	    		str = name.split(' ')
    	    		if(str.length > 1){
    	    			tmp["default_first_name"] = str[0]
    	    			last_name = ''
    	    			for(i=1;i<str.length;i++){
    	    				last_name= last_name + " " + str[i]
    	    			}
    	    			tmp["default_last_name"] = last_name
    	    		}else if(str.length == 1){
    	    			tmp["default_first_name"] = str[0]
    	    		}
    	    	}
    	        var field = (this.options || {}).create_name_field;
    	        if (field === undefined)
    	            field = "name";
    	        if (field !== false && name && (this.options || {}).quick_create !== false)
    	            tmp["default_" + field] = name;
    	        return tmp;
    	    },
    };

    instance.web.form.FieldMany2One = instance.web.form.AbstractField.extend(instance.web.form.CompletionFieldMixin, instance.web.form.ReinitializeFieldMixin, {
        template: "FieldMany2One",
        events: {
            'keydown input': function (e) {
                switch (e.which) {
                case $.ui.keyCode.UP:
                case $.ui.keyCode.DOWN:
                    e.stopPropagation();
                }
            },
        },
        init: function(field_manager, node) {
            this._super(field_manager, node);
            instance.web.form.CompletionFieldMixin.init.call(this);
            this.set({'value': false});
            this.display_value = {};
            this.last_search = [];
            this.floating = false;
            this.current_display = null;
            this.is_started = false;
        },
        reinit_value: function(val) {
            this.internal_set_value(val);
            this.floating = false;
            if (this.is_started)
                this.render_value();
        },
        initialize_field: function() {
            this.is_started = true;
            instance.web.bus.on('click', this, function() {
                if (!this.get("effective_readonly") && this.$input && this.$input.autocomplete('widget').is(':visible')) {
                    this.$input.autocomplete("close");
                }
            });
            instance.web.form.ReinitializeFieldMixin.initialize_field.call(this);
        },
        initialize_content: function() {
            if (!this.get("effective_readonly"))
                this.render_editable();
        },
        destroy_content: function () {
            if (this.$drop_down) {
                this.$drop_down.off('click');
                delete this.$drop_down;
            }
            if (this.$input) {
                this.$input.closest(".ui-dialog .ui-dialog-content").off('scroll');
                this.$input.off('keyup blur autocompleteclose autocompleteopen ' +
                                'focus focusout change keydown');
                delete this.$input;
            }
            if (this.$follow_button) {
                this.$follow_button.off('blur focus click');
                delete this.$follow_button;
            }
        },
        destroy: function () {
            this.destroy_content();
            return this._super();
        },
        init_error_displayer: function() {
            // nothing
        },
        hide_error_displayer: function() {
            // doesn't work
        },
        show_error_displayer: function() {
            new instance.web.form.M2ODialog(this).open();
        },
        render_editable: function() {
            var self = this;
            this.$input = this.$el.find("input");

            this.init_error_displayer();

            self.$input.on('focus', function() {
                self.hide_error_displayer();
            });

            this.$drop_down = this.$el.find(".oe_m2o_drop_down_button");
            this.$follow_button = $(".oe_m2o_cm_button", this.$el);

            this.$follow_button.click(function(ev) {
                ev.preventDefault();
                if (!self.get('value')) {
                    self.focus();
                    return;
                }
                var pop = new instance.web.form.FormOpenPopup(self);
                pop.show_element(
                    self.field.relation,
                    self.get("value"),
                    self.build_context(),
                    {
                        title: _t("Open: ") + self.string
                    }
                );
                pop.on('write_completed', self, function(){
                    self.display_value = {};
                    self.render_value();
                    self.focus();
                    self.view.do_onchange(self);
                });
            });

            // some behavior for input
            var input_changed = function() {
                if (self.current_display !== self.$input.val()) {
                    self.current_display = self.$input.val();
                    if (self.$input.val() === "") {
                        self.internal_set_value(false);
                        self.floating = false;
                    } else {
                        self.floating = true;
                    }
                }
            };
            this.$input.keydown(input_changed);
            this.$input.change(input_changed);
            this.$drop_down.click(function() {
                if (self.$input.autocomplete("widget").is(":visible")) {
                    self.$input.autocomplete("close");
                    self.$input.focus();
                } else {
                    if (self.get("value") && ! self.floating) {
                        self.$input.autocomplete("search", "");
                    } else {
                        self.$input.autocomplete("search");
                    }
                }
            });

            // Autocomplete close on dialog content scroll
            var close_autocomplete = _.debounce(function() {
                if (self.$input.autocomplete("widget").is(":visible")) {
                    self.$input.autocomplete("close");
                }
            }, 50);
            this.$input.closest(".ui-dialog .ui-dialog-content").on('scroll', this, close_autocomplete);

            self.ed_def = $.Deferred();
            self.uned_def = $.Deferred();
            var ed_delay = 200;
            var ed_duration = 15000;
            var anyoneLoosesFocus = function (e) {
                var used = false;
                if (self.floating) {
                    if (self.last_search.length > 0) {
                        if (self.last_search[0][0] != self.get("value")) {
                            self.display_value = {};
                            self.display_value["" + self.last_search[0][0]] = self.last_search[0][1];
                            self.reinit_value(self.last_search[0][0]);
                        } else {
                            used = true;
                            self.render_value();
                        }
                    } else {
                        used = true;
                        self.reinit_value(false);
                    }
                    self.floating = false;
                }
                if (used && self.get("value") === false && ! self.no_ed) {
                    self.ed_def.reject();
                    self.uned_def.reject();
                    self.ed_def = $.Deferred();
                    self.ed_def.done(function() {
                        self.show_error_displayer();
                        ignore_blur = false;
                        self.trigger('focused');
                    });
                    ignore_blur = true;
                    setTimeout(function() {
                        self.ed_def.resolve();
                        self.uned_def.reject();
                        self.uned_def = $.Deferred();
                        self.uned_def.done(function() {
                            self.hide_error_displayer();
                        });
                        setTimeout(function() {self.uned_def.resolve();}, ed_duration);
                    }, ed_delay);
                } else {
                    self.no_ed = false;
                    self.ed_def.reject();
                }
            };
            var ignore_blur = false;
            this.$input.on({
                focusout: anyoneLoosesFocus,
                focus: function () { self.trigger('focused'); },
                autocompleteopen: function () { ignore_blur = true; },
                autocompleteclose: function () { ignore_blur = false; },
                blur: function () {
                    // autocomplete open
                    if (ignore_blur) { return; }
                    if (_(self.getChildren()).any(function (child) {
                        return child instanceof instance.web.form.AbstractFormPopup;
                    })) { return; }
                    self.trigger('blurred');
                }
            });

            var isSelecting = false;
            // autocomplete
            this.$input.autocomplete({
                source: function(req, resp) {
                    self.get_search_result(req.term).done(function(result) {
                        resp(result);
                    });
                },
                select: function(event, ui) {
                    isSelecting = true;
                    var item = ui.item;
                    if (item.id) {
                        self.display_value = {};
                        self.display_value["" + item.id] = item.name;
                        self.reinit_value(item.id);
                    } else if (item.action) {
                        item.action();
                        // Cancel widget blurring, to avoid form blur event
                        self.trigger('focused');
                        return false;
                    }
                },
                focus: function(e, ui) {
                    e.preventDefault();
                },
                html: true,
                // disabled to solve a bug, but may cause others
                //close: anyoneLoosesFocus,
                minLength: 0,
                delay: 0
            });
            this.$input.autocomplete("widget").openerpClass();
            // used to correct a bug when selecting an element by pushing 'enter' in an editable list
            this.$input.keyup(function(e) {
                if (e.which === 13) { // ENTER
                    if (isSelecting)
                        e.stopPropagation();
                }
                isSelecting = false;
            });
            this.setupFocus(this.$follow_button);
        },
        render_value: function(no_recurse) {
            var self = this;
            if (! this.get("value")) {
                this.display_string("");
                return;
            }
            var display = this.display_value["" + this.get("value")];
            if (display) {
                this.display_string(display);
                return;
            }
            if (! no_recurse) {
                var dataset = new instance.web.DataSetStatic(this, this.field.relation, self.build_context());
                this.alive(dataset.name_get([self.get("value")])).done(function(data) {
                    self.display_value["" + self.get("value")] = data[0][1];
                    self.render_value(true);
                });
            }
        },
        display_string: function(str) {
            var self = this;
            if (!this.get("effective_readonly")) {
                this.$input.val(str.split("\n")[0]);
                this.current_display = this.$input.val();
                if (this.is_false()) {
                    this.$('.oe_m2o_cm_button').css({'display':'none'});
                } else {
                    this.$('.oe_m2o_cm_button').css({'display':'inline'});
                }
            } else {
                var lines = _.escape(str).split("\n");
                var link = "";
                var follow = "";
                link = lines[0];
                follow = _.rest(lines).join("<br />");
                if (follow)
                    link += "<br />";
                var $link = this.$el.find('.oe_form_uri')
                     .unbind('click')
                     .html(link);
                if (! this.options.no_open)
                    $link.click(function () {
                        self.do_action({
                            type: 'ir.actions.act_window',
                            res_model: self.field.relation,
                            res_id: self.get("value"),
                            views: [[false, 'form']],
                            target: 'current',
                            context: self.build_context().eval(),
                        });
                        return false;
                     });
                $(".oe_form_m2o_follow", this.$el).html(follow);
            }
        },
        set_value: function(value_) {
            var self = this;
            if (value_ instanceof Array) {
                this.display_value = {};
                if (! this.options.always_reload) {
                    this.display_value["" + value_[0]] = value_[1];
                }
                value_ = value_[0];
            }
            value_ = value_ || false;
            this.reinit_value(value_);
        },
        get_displayed: function() {
            return this.display_value["" + this.get("value")];
        },
        add_id: function(id) {
            this.display_value = {};
            this.reinit_value(id);
        },
        is_false: function() {
            return ! this.get("value");
        },
        focus: function () {
            var input = !this.get('effective_readonly') && this.$input && this.$input[0];
            return input ? input.focus() : false;
        },
        _quick_create: function() {
            this.no_ed = true;
            this.ed_def.reject();
            return instance.web.form.CompletionFieldMixin._quick_create.apply(this, arguments);
        },
        _search_create_popup: function() {
            this.no_ed = true;
            this.ed_def.reject();
            return instance.web.form.CompletionFieldMixin._search_create_popup.apply(this, arguments);
        },
        set_dimensions: function (height, width) {
            this._super(height, width);
            this.$input.css('height', height);
        }
    });
};
