from __future__ import annotations

from moriyama_mail.domain.models import Campaign, CampaignStatus


def derive_status(campaign: Campaign) -> CampaignStatus:
    if campaign.error_message:
        return CampaignStatus.ERROR
    if campaign.production_sent:
        return CampaignStatus.PRODUCTION_SENT
    if campaign.delivery_mode.value == "production" and campaign.mail_ready and campaign.test_sent:
        return CampaignStatus.PRODUCTION_READY
    if campaign.delivery_mode.value == "production" and campaign.mail_ready:
        return CampaignStatus.AWAITING_CONFIRMATION
    if campaign.test_sent:
        return CampaignStatus.TEST_SENT
    if campaign.mail_ready:
        return CampaignStatus.MAIL_CREATED
    if campaign.audience_loaded and campaign.share_url_ready:
        return CampaignStatus.AUDIENCE_CONFIRMED
    if campaign.share_url_ready:
        return CampaignStatus.DRIVE_REGISTERED
    if campaign.material_selected:
        return CampaignStatus.MATERIALS_PREPARING
    return CampaignStatus.RECEIVED


def apply_derived_status(campaign: Campaign) -> Campaign:
    campaign.status = derive_status(campaign)
    return campaign
