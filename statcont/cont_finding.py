import astropy
from astropy.stats import sigma_clip
import numpy as np
from scipy import stats
from scipy.optimize import leastsq

##======================================================================
def c_max(flux, rms_noise):
    """
    Perform histogram distribution of variable flux, and determine
    the flux level of the maximum of the histogram
    
    Parameters
    ----------
    flux : np.ndarray
        One-dimension array of flux values
    rms_noise : float
        The estimated RMS noise level of the data
    
    Returns
    -------
    maximum_flux : float
        The measured continuum flux as the maximum of the histogram
    """
    
    all_bins, all_hist, sel_bins, sel_hist, sel_flux = cont_histo(flux, rms_noise)
    
    maximum_flux = all_bins[(np.where(all_hist == all_hist.max())[0])[0]]
    
    return maximum_flux

##======================================================================
def c_mean(flux, rms_noise):
    """
    Perform mean of the distribution of variable flux, and determine
    the mean of a selected range around the maximum of the histogram
    
    Parameters
    ----------
    flux : np.ndarray
        One-dimension array of flux values
    rms_noise : float
        The estimated RMS noise level of the data
    
    Returns
    -------
    mean_flux : float
        The measured continuum flux as the mean of the distribution
    meansel_flux : float
        The measured continuum flux as the mean of a selected range
        around the maximum of the distribution
    """
    
    all_bins, all_hist, sel_bins, sel_hist, sel_flux = cont_histo(flux, rms_noise)
    
    mean_flux = np.mean(flux)
    meansel_flux = np.mean(sel_flux)
    
    return mean_flux, meansel_flux

##======================================================================
def c_median(flux, rms_noise):
    """
    Perform median of the distribution of variable flux, and determine
    the median of a selected range around the maximum of the histogram
    
    Parameters
    ----------
    flux : np.ndarray
        One-dimension array of flux values
    rms_noise : float
        The estimated RMS noise level of the data
    
    Returns
    -------
    median_flux : float
        The measured continuum flux as the median of the distribution
    mediansel_flux : float
        The measured continuum flux as the median of a selected range
        around the maximum of the distribution
    """
    
    all_bins, all_hist, sel_bins, sel_hist, sel_flux = cont_histo(flux, rms_noise)
    
    median_flux = np.median(flux)
    mediansel_flux = np.median(sel_flux)
    
    return median_flux, mediansel_flux

##======================================================================
def c_percent(flux, percentile):
    """
    Perform numpy percentile to determine the level of the selected
    percentile
    
    Parameters
    ----------
    flux : np.ndarray
        One-dimension array of flux values
    percentile : float
        The selected percentile
    
    Returns
    -------
    percent_flux : float
        The measured continuum flux at the selected percentile
    """
    
    percent_flux = np.percentile(flux, percentile)
    
    return percent_flux

##======================================================================
def c_KDEmax(flux, rms_noise):
    """
    Perform KDE of the distribution and determine the position of the
    maximum
    
    Parameters
    ----------
    flux : np.ndarray
        One-dimension array of flux values
    rms_noise : float
        The estimated RMS noise level of the data
    
    Returns
    -------
    KDEmax_flux : float
        The measured continuum flux as the position of the maximum
        of the KDE
    """

    KDE_bandwidth = rms_noise/10.
    scipy_kde = stats.gaussian_kde(flux, bw_method=KDE_bandwidth)
    KDExmin, KDExmax = min(flux), max(flux)
    KDEx = np.mgrid[KDExmin:KDExmax:100j]
    positions = np.vstack([KDEx.ravel()])
    KDEpos = scipy_kde(positions)
    KDEmax_flux = positions.T[np.argmax(KDEpos)]
    
    return KDEmax_flux

##======================================================================
def c_Gaussian(flux, rms_noise):
    """
    Perform Gaussian fit to the distribution of variable flux, and determine
    the center and width of the Gaussian. Similarly, perform the Gaussian
    fit to a selected range of the distribution around the maximum of
    the histogram, and determine the center and width of the new Gaussian
    
    Parameters
    ----------
    flux : np.ndarray
        One-dimension array of flux values
    rms_noise : float
        The estimated RMS noise level of the data
    
    Returns
    -------
    Gaussian_flux : float
    Gaussian_noise : float
        The measured continuum flux and estimated 1-sigma noise as the
        center and width of the Gaussian fit to the histogram distribution
        The estimated 1-sigma per-channel noise around that measurement
    GaussNw_flux : float
    GaussNw_noise : float
        The measured continuum flux and estimated 1-sigma noise as the
        center and width of the Gaussian fit to a selected range around
        the maximum of the distribution
    """

    fitfunc = lambda p, x: p[0]*np.exp(-0.5*((x-p[1])/p[2])**2.)
    errfunc = lambda p, x, y: (y - fitfunc(p, x))
    
    all_bins, all_hist, sel_bins, sel_hist, sel_flux = cont_histo(flux, rms_noise)

    meansel_flux = np.mean(sel_flux)
    meansel_sigma = np.std(sel_flux)

    init = [all_hist.max(), meansel_flux, meansel_sigma]
    out = leastsq(errfunc, init, args=(all_bins, all_hist))
    c = out[0]
    Gaussian_flux = c[1]
    Gaussian_noise = c[2]

    init = [all_hist.max(), meansel_flux, meansel_sigma]
    out = leastsq(errfunc, init, args=(sel_bins, sel_hist))
    d = out[0]
    GaussNw_flux = d[1]
    GaussNw_noise = d[2]
    
    return Gaussian_flux, Gaussian_noise, GaussNw_flux, GaussNw_noise

##======================================================================
def c_sigmaclip(flux, rms_noise, sigma_clip_threshold=1.8):
    """
    Perform sigma-clipping to determine the mean flux level, with different
    adaptations for emission- and absorption-dominated spectra

    Parameters
    ----------
    flux : np.ndarray
        One-dimension array of flux values
    rms_noise : float
        The estimated RMS noise level of the data
    sigma_clip_threshold : float
        The threshold in number of sigma above/below which to reject outlier
        data

    Returns
    -------
    sigmaclip_flux : float
    sigmaclip_noise : float
        The measured continuum flux and estimated 1-sigma per-channel noise
        around that measurement
    """

    # Sigma-clipping method applied to the flux array
    if astropy.version.major >= 1:
        filtered_data = sigma_clip(flux, sigma=sigma_clip_threshold,
                                   iters=None)
    elif astropy.version.major < 1:
        filtered_data = sigma_clip(flux, sig=sigma_clip_threshold, iters=None)

    sigmaclip_flux_prev = sigmaclip_flux = np.mean(filtered_data)
    sigmaclip_noise = sigmaclip_sigma = np.std(filtered_data)
    mean_flux = np.mean(flux)

    # For EMISSION-dominated spectra
    if (mean_flux-sigmaclip_flux_prev) > (+1.0*rms_noise):
        sigmaclip_flux = sigmaclip_flux_prev - sigmaclip_sigma
    # For ABSORPTION-dominated spectra
    elif (mean_flux-sigmaclip_flux_prev) < (-1.0*rms_noise):
        sigmaclip_flux = sigmaclip_flux_prev + sigmaclip_sigma

    return sigmaclip_flux, sigmaclip_noise

##======================================================================
def cont_histo(flux, rms_noise):
    """
    Create histogram distribution of the flux data
    and select a narrower range around the maximum
    of the histogram distribution
    
    Parameters
    ----------
    flux : np.ndarray
        One-dimension array of flux values
    rms_noise : float
        The estimated RMS noise level of the data
    
    Returns
    -------
    all_bins : np.ndarray
        One-dimension array with the value of bins of the histogram
    all_hist : np.ndarray
        One-dimension array with the value of the position of the bins
    sel_bins : np.ndarray
        One-dimension array with the value of bins of the histogram
        for the selected bins around the maximum
    sel_hist : np.ndarray
        One-dimension array with the value of position of the bins
        for the selected bins around the maximum
    sel_flux : np.ndarray
        One-dimension array of the flux values selected
        around the maximum of the histogram
    """
    
    #
    # creating a general histogram of the flux data
    # main variables are:
    #   all_hist     - counts in each bin of the histogram
    #   all_bins     - location of the bins (fluxes)
    #   all_number_* - index of the array
    number_bins = int((np.amax(flux)-np.amin(flux))/(2*rms_noise))
    all_hist, all_bin_edges = np.histogram(flux, number_bins)
    all_bins = all_bin_edges[0:len(all_bin_edges)-1]
    all_bins = [x + (all_bins[1]-all_bins[0])/2. for x in all_bins]
    all_number_max_array = (np.where(all_hist == all_hist.max())[0])
    all_number_max = all_number_max_array[0]
    all_bins_max = (all_bin_edges[all_number_max] + (all_bins[1]-all_bins[0])/2.)

    # Gaussian fit around the maximum of the distribution
    # determining the range to fit the Gaussian function
    all_number_left  = (np.where(((all_hist == 0) & (all_bins <= all_bins_max)) | (all_bins == all_bins[0]))[0]).max()
    all_number_right = (np.where(((all_hist == 0) & (all_bins >= all_bins_max)) | (all_bins == all_bins[number_bins-1]))[0]).min()
    all_number_total = abs(all_number_right-all_number_max)+abs(all_number_left-all_number_max)
    emission_absorption_ratio = abs(all_number_right-all_number_max)*1.0/(all_number_total*1.0)
    if (emission_absorption_ratio >= 0.66):
        lower_all_bins = all_bins_max - 8. * (all_bins[1]-all_bins[0])
        upper_all_bins = all_bins_max + 4. * (all_bins[1]-all_bins[0])
    if (emission_absorption_ratio <= 0.33):
        lower_all_bins = all_bins_max - 4. * (all_bins[1]-all_bins[0])
        upper_all_bins = all_bins_max + 8. * (all_bins[1]-all_bins[0])
    if ((emission_absorption_ratio > 0.33) and (emission_absorption_ratio < 0.66)):
        lower_all_bins = all_bins_max - 5. * (all_bins[1]-all_bins[0])
        upper_all_bins = all_bins_max + 5. * (all_bins[1]-all_bins[0])
    sel_bins_array = np.where((all_bins >= lower_all_bins) & (all_bins <= upper_all_bins))[0]
    if (len(sel_bins_array) < 3):
        sel_bins_array = [sel_bins_array[0]-2, sel_bins_array[0]-1, sel_bins_array[0], sel_bins_array[0]+1, sel_bins_array[0]+2]
        lower_all_bins = all_bins[sel_bins_array[0]]
        upper_all_bins = all_bins[sel_bins_array[len(sel_bins_array)-1]]
    sel_bins = all_bins[sel_bins_array[0]:sel_bins_array[len(sel_bins_array)-1]+1]
    sel_hist = all_hist[sel_bins_array[0]:sel_bins_array[len(sel_bins_array)-1]+1]
    sel_flux = flux[(flux >= lower_all_bins) & (flux <= upper_all_bins)]
    
    return all_bins, all_hist, sel_bins, sel_hist, sel_flux