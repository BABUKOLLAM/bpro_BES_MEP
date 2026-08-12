from odoo import http
from odoo.exceptions import UserError
from odoo.http import request


class BproOfferPortal(http.Controller):
    """Public candidate-facing offer page. auth="public": the
    access_token in the URL IS the authentication, following the same
    portal.mixin pattern Odoo itself uses for e.g. sale order share
    links - not a login-gated route.
    """

    def _get_offer_or_404(self, offer_id, token):
        offer = request.env["bpro.job.offer"].sudo().browse(int(offer_id))
        if not offer.exists() or offer.access_token != token:
            return None
        return offer

    @http.route(
        '/bpro/offer/<int:offer_id>', type='http', auth='public',
        website=True, sitemap=False,
    )
    def offer_view(self, offer_id, access_token=None, **kwargs):
        offer = self._get_offer_or_404(offer_id, access_token)
        if not offer:
            return request.not_found()
        return request.render('bpro_recruitment.portal_offer_page', {
            'offer': offer,
            'access_token': access_token,
        })

    @http.route(
        '/bpro/offer/<int:offer_id>/submit', type='http', auth='public',
        website=True, sitemap=False, methods=['POST'],
    )
    def offer_submit(self, offer_id, access_token=None, **post):
        offer = self._get_offer_or_404(offer_id, access_token)
        if not offer:
            return request.not_found()
        if offer.state != 'sent':
            return request.redirect(f'/bpro/offer/{offer_id}?access_token={access_token}')

        offer.write({
            'candidate_address': post.get('candidate_address'),
            'candidate_dob': post.get('candidate_dob') or False,
            'candidate_pan': post.get('candidate_pan'),
            'candidate_aadhar': post.get('candidate_aadhar'),
            'candidate_emergency_contact_name': post.get('candidate_emergency_contact_name'),
            'candidate_emergency_contact_phone': post.get('candidate_emergency_contact_phone'),
            'candidate_bank_account_number': post.get('candidate_bank_account_number'),
            'candidate_bank_ifsc': post.get('candidate_bank_ifsc'),
        })

        decision = post.get('decision')
        try:
            if decision == 'accept':
                offer.action_accept_from_portal()
            elif decision == 'decline':
                offer.action_decline_from_portal(reason=post.get('declined_reason'))
        except UserError:
            pass

        return request.redirect(f'/bpro/offer/{offer_id}?access_token={access_token}')
