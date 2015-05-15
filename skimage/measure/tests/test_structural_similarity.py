import os
import numpy as np
import scipy.io
from numpy.testing import (assert_equal, assert_raises, assert_almost_equal,
                           assert_array_almost_equal)

from skimage.measure import structural_similarity as ssim
from skimage.measure._structural_similarity import (gaussian_filter2)
import skimage.data
from skimage.io import imread
from skimage import data_dir

np.random.seed(5)
cam = skimage.data.camera()
sigma = 20.0
cam_noisy = np.clip(cam + sigma * np.random.randn(*cam.shape), 0, 255)
cam_noisy = cam_noisy.astype(cam.dtype)

np.random.seed(1234)

def test_ssim_patch_range():
    N = 51
    X = (np.random.rand(N, N) * 255).astype(np.uint8)
    Y = (np.random.rand(N, N) * 255).astype(np.uint8)

    assert(ssim(X, Y, win_size=N) < 0.1)
    assert_equal(ssim(X, X, win_size=N), 1)


def test_ssim_image():
    N = 100
    X = (np.random.rand(N, N) * 255).astype(np.uint8)
    Y = (np.random.rand(N, N) * 255).astype(np.uint8)

    S0 = ssim(X, X, win_size=3)
    assert_equal(S0, 1)

    S1 = ssim(X, Y, win_size=3)
    assert(S1 < 0.3)

    S2 = ssim(X, Y, win_size=11, gaussian_weights=True)
    assert(S1 < 0.3)

    mssim0, S3 = ssim(X, Y, full=True)
    assert_equal(S3.shape, X.shape)
    mssim = ssim(X, Y)
    assert_equal(mssim0, mssim)

    # ssim of image with itself should be 1.0
    assert_equal(ssim(X, X), 1.0)


# NOTE: This test is known to randomly fail on some systems (Mac OS X 10.6)
def test_ssim_grad():
    N = 30
    X = np.random.rand(N, N) * 255
    Y = np.random.rand(N, N) * 255

    f = ssim(X, Y, dynamic_range=255)
    g = ssim(X, Y, dynamic_range=255, gradient=True)

    assert f < 0.05
    assert g[0] < 0.05
    assert np.all(g[1] < 0.05)

    mssim, grad, s = ssim(X, Y, dynamic_range=255, gradient=True, full=True)
    assert np.all(grad < 0.05)


def test_ssim_dtype():
    N = 30
    X = np.random.rand(N, N)
    Y = np.random.rand(N, N)

    S1 = ssim(X, Y)

    X = (X * 255).astype(np.uint8)
    Y = (X * 255).astype(np.uint8)

    S2 = ssim(X, Y)

    assert S1 < 0.1
    assert S2 < 0.1


def test_ssim_multichannel():
    N = 100
    X = (np.random.rand(N, N) * 255).astype(np.uint8)
    Y = (np.random.rand(N, N) * 255).astype(np.uint8)

    S1 = ssim(X, Y, win_size=3)

    # replicate across three channels.  should get identical value
    Xc = np.tile(X[..., np.newaxis], (1, 1, 3))
    Yc = np.tile(Y[..., np.newaxis], (1, 1, 3))
    S2 = ssim(Xc, Yc, win_size=3)
    assert_almost_equal(S1, S2)

    # full case should return an image as well
    m, S3 = ssim(Xc, Yc, full=True)
    assert_equal(S3.shape, Xc.shape)

    # gradient case
    m, grad = ssim(Xc, Yc, gradient=True)
    assert_equal(grad.shape, Xc.shape)

    # full and gradient case
    m, grad, S3 = ssim(Xc, Yc, full=True, gradient=True)
    assert_equal(grad.shape, Xc.shape)
    assert_equal(S3.shape, Xc.shape)

    # fail if win_size exceeds any non-channel dimension
    assert_raises(ValueError, ssim, Xc, Yc, win_size=7, multichannel=False)


def test_ssim_nD():
    # test 1D through 4D on small random arrays
    N = 10
    for ndim in range(1, 5):
        xsize = [N, ] * 5
        X = (np.random.rand(*xsize) * 255).astype(np.uint8)
        Y = (np.random.rand(*xsize) * 255).astype(np.uint8)

        mssim = ssim(X, Y, win_size=3)
        assert mssim < 0.05


def test_ssim_multichannel_chelsea():
    # color image example
    Xc = skimage.data.chelsea()
    sigma = 15.0
    Yc = np.clip(Xc + sigma * np.random.randn(*Xc.shape), 0, 255)
    Yc = Yc.astype(Xc.dtype)

    # multichannel result should be mean of the individual channel results
    mssim = ssim(Xc, Yc)
    mssim_sep = [ssim(Yc[..., c], Xc[..., c]) for c in range(Xc.shape[-1])]
    assert_almost_equal(mssim, np.mean(mssim_sep))

    # ssim of image with itself should be 1.0
    assert_equal(ssim(Xc, Xc), 1.0)


def test_gaussian_mssim_vs_IPOL():
    # Tests vs. imdiff result from the following IPOL article and code:
    # http://www.ipol.im/pub/art/2011/g_lmii/
    mssim_IPOL = 0.327309966087341
    mssim = ssim(cam, cam_noisy, gaussian_weights=True,
                 use_sample_covariance=False)
    assert_almost_equal(mssim, mssim_IPOL, decimal=5)


def test_gaussian_mssim_vs_author_ref():
    """
    test vs. result from original author's Matlab implementation available at
    https://ece.uwaterloo.ca/~z70wang/research/ssim/

    Matlab test code:
       img1 = imread('camera.png')
       img2 = imread('camera_noisy.png')
       mssim = ssim_index(img1, img2)
    """
    mssim_matlab = 0.218987555561590
    mssim = ssim(cam, cam_noisy, gaussian_weights=True,
                 use_sample_covariance=False)
    assert_almost_equal(mssim, mssim_matlab, decimal=7)


def test_gaussian_mssim_and_gradient_vs_Matlab():
    # comparison to Matlab implementation of N. Avanaki:
    # https://ece.uwaterloo.ca/~nnikvand/Coderep/SHINE%20TOOLBOX/SHINEtoolbox/
    # Note: final line of ssim_sens.m was modified to discard image borders

    ref = np.load(os.path.join(data_dir, 'mssim_matlab_output.npz'))
    grad_matlab = ref['grad_matlab']
    mssim_matlab = float(ref['mssim_matlab'])

    mssim, grad = ssim(cam, cam_noisy, gaussian_weights=True, gradient=True,
                       use_sample_covariance=False)

    assert_almost_equal(mssim, mssim_matlab, decimal=7)

    # check almost equal aside from object borders
    assert_array_almost_equal(grad_matlab[5:-5], grad[5:-5])


def test_mssim_vs_legacy():
    # check that ssim with default options matches skimage 0.11 result
    mssim_skimage_0pt11 = 0.34192589699605191
    mssim = ssim(cam, cam_noisy)
    assert_almost_equal(mssim, mssim_skimage_0pt11)


def test_invalid_input():
    X = np.zeros((3, 3), dtype=np.double)
    Y = np.zeros((3, 3), dtype=np.int)
    assert_raises(ValueError, ssim, X, Y)

    Y = np.zeros((4, 4), dtype=np.double)
    assert_raises(ValueError, ssim, X, Y)

    assert_raises(ValueError, ssim, X, X, win_size=8)

    # do not allow both image content weighting and gradient calculation
    assert_raises(ValueError, ssim, X, X, image_content_weighting=True,
                  gradient=True)
    # some kwarg inputs must be non-negative
    assert_raises(ValueError, ssim, X, X, K1=-0.1)
    assert_raises(ValueError, ssim, X, X, K2=-0.1)
    assert_raises(ValueError, ssim, X, X, sigma=-1.0)


def test_gaussian_filter2():
    # expected result for filtering a 2D dirac delta
    res = np.array(
        [[0.01441882,  0.02808402,  0.03507270,  0.02808402,  0.01441882],
         [0.02808402,  0.05470021,  0.06831229,  0.05470021,  0.02808402],
         [0.03507270,  0.06831229,  0.08531173,  0.06831229,  0.03507270],
         [0.02808402,  0.05470021,  0.06831229,  0.05470021,  0.02808402],
         [0.01441882,  0.02808402,  0.03507270,  0.02808402,  0.01441882]])

    x = np.zeros((11, 11))
    x[5, 5] = 1  # centered direc delta
    xf = gaussian_filter2(x, sigma=1.5, size=5)

    assert_array_almost_equal(xf[3:8, 3:8], res)
    # zeros elsewhere
    assert np.all(xf[-3:, :] == 0)
    assert np.all(xf[:3, :] == 0)
    assert np.all(xf[:, -3:] == 0)
    assert np.all(xf[:, :3] == 0)


if __name__ == "__main__":
    np.testing.run_module_suite()
