# -*- coding: utf-8 -*-
# from odoo import http


# class Shunfeng(http.Controller):
#     @http.route('/shunfeng/shunfeng/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/shunfeng/shunfeng/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('shunfeng.listing', {
#             'root': '/shunfeng/shunfeng',
#             'objects': http.request.env['shunfeng.shunfeng'].search([]),
#         })

#     @http.route('/shunfeng/shunfeng/objects/<model("shunfeng.shunfeng"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('shunfeng.object', {
#             'object': obj
#         })
