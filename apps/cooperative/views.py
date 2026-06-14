import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum
from .models import Cooperative, Branch
from apps.core.utils import get_cooperative_id
from apps.core.permissions import permission_required, user_can


@permission_required('cooperative.profile')
def cooperative_profile(request):
    cooperative_id = get_cooperative_id(request)
    if not cooperative_id and request.user.role == 'super_admin':
        cooperative_id = request.session.get('cooperative_id')
        if not cooperative_id:
            cooperative_id = Cooperative.objects.order_by('id').values_list('id', flat=True).first()
    if not cooperative_id:
        messages.error(request, 'No cooperative selected')
        return redirect('core:super_admin_dashboard')
    cooperative = get_object_or_404(Cooperative, id=cooperative_id)
    can_edit = user_can(request.user, 'cooperative.admin')
    if request.method == 'POST':
        if not can_edit:
            messages.error(
                request,
                'Huna ruhusa ya kuhariri wasifu wa chama. / You cannot edit the cooperative profile.',
            )
            return redirect('cooperative:profile')
        cooperative.name = request.POST.get('name', cooperative.name)
        cooperative.address = request.POST.get('address', cooperative.address)
        cooperative.city = request.POST.get('city', cooperative.city)
        cooperative.region = request.POST.get('region', cooperative.region)
        cooperative.phone = request.POST.get('phone', cooperative.phone)
        cooperative.email = request.POST.get('email', cooperative.email)
        cooperative.vision = request.POST.get('vision', cooperative.vision)
        cooperative.mission = request.POST.get('mission', cooperative.mission)
        if request.FILES.get('logo'):
            cooperative.logo = request.FILES['logo']
        cooperative.save()
        messages.success(request, 'Cooperative profile updated successfully')
        return redirect('cooperative:profile')

    return render(request, 'cooperative/profile.html', {
        'cooperative': cooperative,
        'can_edit_coop': can_edit,
    })


@permission_required('cooperative.admin')
def branches(request):
    cooperative_id = get_cooperative_id(request)
    branch_list = Branch.objects.all()
    if cooperative_id:
        branch_list = branch_list.filter(cooperative_id=cooperative_id)
    return render(request, 'cooperative/branches.html', {'branches': branch_list})


@permission_required('cooperative.admin')
def branch_create(request):
    cooperative_id = get_cooperative_id(request)
    if not cooperative_id:
        messages.error(request, 'No cooperative selected')
        return redirect('core:super_admin_dashboard')
    if request.method == 'POST':
        cooperative = get_object_or_404(Cooperative, id=cooperative_id)
        Branch.objects.create(
            cooperative=cooperative,
            name=request.POST.get('name'),
            code=request.POST.get('code'),
            address=request.POST.get('address', ''),
            city=request.POST.get('city', ''),
            region=request.POST.get('region', ''),
            phone=request.POST.get('phone', ''),
            email=request.POST.get('email', ''),
        )
        messages.success(request, 'Branch created successfully')
        return redirect('cooperative:branches')
    return render(request, 'cooperative/branch_form.html', {'title': 'Create Branch'})


@permission_required('cooperative.admin')
def cooperative_toggle_status(request, cooperative_id):
    cooperative = get_object_or_404(Cooperative, id=cooperative_id)
    cooperative.status = 'inactive' if cooperative.status == 'active' else 'active'
    cooperative.save()
    messages.success(request, f'Cooperative status changed to {cooperative.status}')
    return redirect(request.META.get('HTTP_REFERER', 'core:super_admin_dashboard'))


@permission_required('cooperative.admin')
def cooperative_create_superadmin(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code', str(uuid.uuid4())[:8])
        coop_type = request.POST.get('type', 'amcos')
        plan = request.POST.get('subscription_plan', 'basic')
        phone = request.POST.get('phone', '')
        email = request.POST.get('email', '')
        city = request.POST.get('city', '')
        region = request.POST.get('region', '')
        if not name:
            messages.error(request, 'Cooperative name is required')
            return redirect('core:super_admin_dashboard')
        if Cooperative.objects.filter(name=name).exists():
            messages.error(request, f'Cooperative "{name}" already exists')
            return redirect('core:super_admin_dashboard')
        coop = Cooperative.objects.create(
            name=name, code=code, type=coop_type,
            subscription_plan=plan, phone=phone, email=email,
            city=city, region=region,
        )
        messages.success(request, f'Cooperative "{name}" created successfully')
        return redirect('core:super_admin_dashboard')
    return redirect('core:super_admin_dashboard')


@permission_required('cooperative.admin')
def cooperative_edit(request, cooperative_id):
    cooperative = get_object_or_404(Cooperative, id=cooperative_id)
    if request.method == 'POST':
        cooperative.name = request.POST.get('name', cooperative.name)
        cooperative.type = request.POST.get('type', cooperative.type)
        cooperative.phone = request.POST.get('phone', cooperative.phone)
        cooperative.email = request.POST.get('email', cooperative.email)
        cooperative.city = request.POST.get('city', cooperative.city)
        cooperative.region = request.POST.get('region', cooperative.region)
        cooperative.subscription_plan = request.POST.get('subscription_plan', cooperative.subscription_plan)
        cooperative.save()
        messages.success(request, f'Cooperative "{cooperative.name}" updated successfully')
        return redirect('core:super_admin_dashboard')
    return render(request, 'cooperative/edit.html', {'cooperative': cooperative})


@permission_required('cooperative.admin')
def cooperative_delete(request, cooperative_id):
    if request.method == 'POST':
        cooperative = get_object_or_404(Cooperative, id=cooperative_id)
        cooperative.delete()
        messages.success(request, 'Cooperative deleted successfully')
    return redirect(request.META.get('HTTP_REFERER', 'core:super_admin_dashboard'))
