# -*- coding: utf-8 -*-
import base64
import hashlib
import json
import logging
import random
import time
import urllib

from encodings.base64_codec import base64_encode

from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement

import requests
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


# class shunfeng(models.Model):
#     _name = 'shunfeng.shunfeng'
#     _description = 'shunfeng.shunfeng'
#
#     stock_ = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()


class shunfeng(models.Model):
    _name = 'shunfeng.shunfeng'
    _description = 'shunfeng.shunfeng'
    
    stock_pick_id = fields.Many2one('stock.picking', string='订单号')
    shunfeng_order_num = fields.Char(string='顺丰订单号')
    shunfeng_num = fields.Char(string='快递单号')
    originCode = fields.Char("原寄地区域代码")
    destCode = fields.Char("目的地区域代码")
    filterResult = fields.Selection([('1', '人工确认'), ('2', '可收派'), ('3', '不可以收派')], string='筛单结果')
    remark = fields.Char('不可以收派的原因代码', help='如果filter_result=3时为必填，不可以收派的原因代码：1：收方超范围2：'
                                            '派方超范围3：其它原因 高峰管控提示信息【数字】：【高峰管控提示信息】'
                                            '(如 4：温馨提示 ，1：春运延时)')
    status = fields.Selection([('1', '下单成功'), ('2', '已取消')], string='订单状态')


class PickingExtra(models.Model):
    _inherit = 'stock.picking'
    
    mail_partner_id = fields.Many2one('res.partner', string='寄件地址')
    sf_num = fields.Char("顺丰单号", required=False)
    is_sf_delivery = fields.Boolean('顺丰发货', default=False, copy=False)
    originCode = fields.Char("原寄地区域代码")
    destCode = fields.Char("目的地区域代码")
    
    def auto_get_mail_partner(self, record):
        """绑定寄件地址"""
        try:
            if record.picking_type_code == 'outgoing':
                partner = self.env['res.partner'].search([('id', '=', 21509)])  # 固定寄件地址
                record.write({
                    'mail_partner_id': partner.id
                })
                self.env.cr.commit()
        except Exception as e:
            _logger.error(e)
    
    def get_shunfeng(self):
        # reqURL = 'https://sfapi-sbox.sf-express.com/std/service'
        reqURL = 'https://sfapi.sf-express.com/std/service'
        # partnerID = 'Y5pyZg'  # 合作伙伴编码（即顾客编码）测试
        # requestID = '8hCQkGNVYtxQXE12RUiKNzuwFO9YhnVp'  # 请求唯一号UUID 测试
        # checkword = '8hCQkGNVYtxQXE12RUiKNzuwFO9YhnVp'  # 校验码 测试
        serviceCode = 'EXP_RECE_CREATE_ORDER'  # 接口服务代码
        timestamp = int(time.time())
        # monthlyCard = ''  # 月结卡号,月结必传
        monthlyCard = ''  # 正式月结卡号
        partnerID = ''  # 正式
        requestID = ''  # 正式
        checkword = ''  # 正式
        
        payMethod = 2  # 1:寄方付 2:收方付  3:第三方付"%s%d%d" % (first, int(time.time()), random.randint(1000, 9999))
        orderId = self.name + random.randint(1000, 9999).__str__()
        # if self.is_cancel_sf:
        #     orderId = orderId + str(self.id)
        res = {
            'code': 200,
            'success': True,
            'message': '',
            'data': []
        }
        sf = self.env['shunfeng.shunfeng'].sudo().search([('shunfeng_num', '=', self.sf_num)])
        if sf and sf.status == '1':
            res['msg'] = '请勿重复下单'
            raise UserError('请勿重复下单')
        if self.state in ('done', 'cancel') or not self.is_delivery:
            res['msg'] = '该订单未审核,不能发货'
            print('订单不能发货5' * 20)
            raise UserError('该订单未审核,不能发货')
        # if self.env['shunfeng.shunfeng'].sudo().search([('stock_pick_id', '=', self.id)]):
        #     print('请勿重复下单5' * 20)
        #     res['msg'] = '请勿重复下单'
        #     raise UserError('请勿重复下单')
        if self.logistics == '1':
            msgData = {'cargoDetails': [], 'contactInfoList': [], 'language': 'zh_CN', 'orderId': orderId,
                       'monthlyCard': monthlyCard}
        elif self.logistics == '2':
            msgData = {'cargoDetails': [], 'contactInfoList': [], 'language': 'zh_CN', 'orderId': orderId,
                       'payMethod': payMethod}
        else:
            raise UserError('请选择物流')
        # msgData = {'cargoDetails': [], 'contactInfoList': [], 'language': 'zh_CN', 'orderId': self.name}
        print(self.move_line_ids_without_package)
        for move_line_ids_without in self.move_line_ids_without_package:
            stock_move_line = self.env['stock.move.line'].sudo().search([('id', '=', move_line_ids_without.id)])
            uom = self.env['uom.uom'].sudo().search([('id', '=', stock_move_line.product_uom_id.id)])
            product = self.env['product.product'].sudo().search([('id', '=', stock_move_line.product_id.id)])
            print(move_line_ids_without)
            print(stock_move_line)
            print(product)
            print('#' * 40)
            
            msgData['cargoDetails'].append({
                'count': stock_move_line.qty_done,
                'unit': uom.name,
                'name': product.name
            })
        # 到件信息
        partner = self.env['res.partner'].sudo().search([('id', '=', self.partner_id.id)])
        if not partner.contact_address:
            res['msg'] = '请填写到件地址'
            raise UserError('请填写到件地址')
        msgData['contactInfoList'].append({
            'address': partner.contact_address,
            'contact': partner.name if partner.name else '未知',
            
            'contactType': 2,  # 地址类型：1：寄件  2：到件
            'country': 'CN',  # 国家代码
            'tel': partner.phone if partner.phone else partner.mobile
        })
        
        # 寄件信息
        mail_partner = self.env['res.partner'].sudo().search([('id', '=', self.mail_partner_id.id)])
        if not mail_partner or not mail_partner.contact_address:
            print('请输入寄件地址5' * 20)
            res['msg'] = '请输入寄件地址'
            return UserError('请输入寄件地址')
        msgData['contactInfoList'].append({
            'address': mail_partner.contact_address,
            'contact': mail_partner.name if mail_partner else 'chicun',
            'contactType': 1,  # 地址类型：1：寄件  2：到件
            'country': 'CN',  # 国家代码
            'tel': mail_partner.phone if mail_partner.phone else mail_partner.mobile
        })
        
        _logger.info(msgData)
        msgData = msgData.__str__()
        str = urllib.parse.quote_plus(msgData + timestamp.__str__() + checkword)
        m = hashlib.md5()
        m.update(str.encode('utf-8'))
        md5Str = m.digest()
        msgDigest = base64.b64encode(md5Str).decode('utf-8')
        print("msgDigest: " + msgDigest)
        data = {"partnerID": partnerID, "requestID": requestID, "serviceCode": serviceCode, "timestamp": timestamp,
                "msgDigest": msgDigest, "msgData": msgData}
        _logger.info(self)
        resp = requests.post(reqURL, data=data)
        con = json.loads(resp.content)
        _logger.info(resp.content)
        
        _logger.info(timestamp)
        originCode = ''
        destCode = ''
        filterResult = ''
        remark = ''
        for key, value in con.items():
            print('%s ---> %s' % (key, value))
            if key == 'apiResultData':
                test = con['apiResultData']
                _logger.info('下单状态success--------------')
                _logger.info(json.loads(test)['success'])
                if not json.loads(test)['success']:
                    res['msg'] = '请勿重复下单'
                    raise UserError('请勿重复下单')
                
                _logger.info(json.loads(test)['msgData']["waybillNoInfoList"])
                li = json.loads(test)['msgData']["waybillNoInfoList"]
                originCode = json.loads(test)['msgData']['originCode']
                destCode = json.loads(test)['msgData']['destCode']
                filterResult = json.loads(test)['msgData']['filterResult']
                remark = json.loads(test)['msgData']['remark']
        _logger.info('下单成功------------------')
        _logger.info(li[0]['waybillNo'])
        sf_ = self.env['shunfeng.shunfeng'].sudo().create({
            'stock_pick_id': self.id,
            'shunfeng_num': li[0]['waybillNo'],
            'originCode': originCode,
            'destCode': destCode,
            'filterResult': filterResult.__str__(),
            'remark': remark.__str__(),
            'status': '1',
            'shunfeng_order_num': orderId
        })
        self.originCode = originCode
        self.destCode = destCode
        _logger.info(sf_)
        stock = self.env['stock.picking'].sudo().search([('id', '=', self.id)])
        stock.write({
            'sf_num': li[0]['waybillNo'],
            'is_sf_delivery': True,
            'logistics_id': li[0]['waybillNo'],
        })
        return res
    
    # def get_shunfeng_cancel(self):
    #     res = {
    #         'code': 200,
    #         'success': True,
    #         'message': '不能取消订单',
    #         'data': []
    #     }
    #     return res
