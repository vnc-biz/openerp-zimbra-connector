openerp.vnc_zimbra_connector = function (session) {
    var _t = session.web._t,
       _lt = session.web._lt;

    session.mail.MessageCommon.include({
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
};
