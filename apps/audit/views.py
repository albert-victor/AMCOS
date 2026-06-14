from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Count
from django.utils import timezone

from .models import AuditTrail, ComplianceCheck, FraudAlert
from apps.core.utils import get_cooperative_id
from apps.core.permissions import permission_required


@permission_required('audit.view')
def audit_trails(request):
    cooperative_id = get_cooperative_id(request)
    action_filter = request.GET.get('action', '')
    entity_filter = request.GET.get('entity', '')

    trails = AuditTrail.objects.all()
    if cooperative_id:
        trails = trails.filter(cooperative_id=cooperative_id)
    if action_filter:
        trails = trails.filter(action=action_filter)
    if entity_filter:
        trails = trails.filter(entity_type=entity_filter)

    actions = AuditTrail.objects.values('action').distinct()
    entities = AuditTrail.objects.values('entity_type').distinct()
    if cooperative_id:
        actions = actions.filter(cooperative_id=cooperative_id)
        entities = entities.filter(cooperative_id=cooperative_id)

    return render(request, 'audit/trails.html', {
        'trails': trails[:100],
        'actions': actions,
        'entities': entities,
    })


@permission_required('audit.view')
def compliance_checks(request):
    cooperative_id = get_cooperative_id(request)
    checks = ComplianceCheck.objects.all()
    if cooperative_id:
        checks = checks.filter(cooperative_id=cooperative_id)

    if request.method == 'POST':
        ComplianceCheck.objects.create(
            cooperative_id=cooperative_id,
            check_type=request.POST.get('check_type'),
            title=request.POST.get('title'),
            description=request.POST.get('description'),
            due_date=request.POST.get('due_date') or None,
        )
        messages.success(request, 'Compliance check created')
        return redirect('audit:compliance')

    return render(request, 'audit/compliance.html', {'checks': checks})


@permission_required('audit.view')
def compliance_update(request, check_id):
    check = ComplianceCheck.objects.get(id=check_id)
    if request.method == 'POST':
        check.status = request.POST.get('status')
        check.findings = request.POST.get('findings', '')
        check.checked_by = request.user.id
        check.checked_at = timezone.now()
        check.save()
        messages.success(request, 'Compliance check updated')
        return redirect('audit:compliance')
    return render(request, 'audit/compliance_update.html', {'check': check})


@permission_required('audit.view')
def fraud_alerts(request):
    cooperative_id = get_cooperative_id(request)
    alerts = FraudAlert.objects.all()
    if cooperative_id:
        alerts = alerts.filter(cooperative_id=cooperative_id)
    return render(request, 'audit/fraud_alerts.html', {
        'alerts': alerts,
        'new_count': alerts.filter(status='new').count(),
    })
